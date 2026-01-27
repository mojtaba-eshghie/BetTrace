"""
Safe Calculator for RAG System.

Provides deterministic calculation capabilities that the LLM can invoke.
All calculations are executed via SQL (inherently sandboxed) or safe Python.

Pattern:
1. LLM analyzes query and determines what calculations are needed
2. LLM requests calculations in structured format
3. This module executes calculations safely (no arbitrary code)
4. Results are returned to LLM for narration

This ensures:
- All math is deterministic (no LLM arithmetic errors)
- Calculations are safe (SQL-based, no code injection)
- Results are auditable (we log what was computed)
"""

import re
import sqlite3
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class CalculationType(Enum):
    """Types of calculations we support."""
    SUM = "sum"
    COUNT = "count"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    DISTINCT_COUNT = "distinct_count"
    LIST = "list"
    TOP_N = "top_n"
    BOTTOM_N = "bottom_n"
    GROUP_BY = "group_by"
    FILTER_COUNT = "filter_count"


@dataclass
class CalculationRequest:
    """A structured calculation request from the LLM."""
    
    calc_type: CalculationType
    column: str  # Column to operate on (e.g., "stake_gbp", "price_delay_ms")
    filters: Optional[Dict[str, Any]] = None  # WHERE conditions
    group_by: Optional[str] = None  # GROUP BY column
    limit: Optional[int] = None  # For TOP_N/BOTTOM_N
    order_desc: bool = True  # For TOP_N (True) vs BOTTOM_N (False)
    
    def to_description(self) -> str:
        """Human-readable description of the calculation."""
        desc = f"{self.calc_type.value.upper()}({self.column})"
        if self.filters:
            filter_str = ", ".join(f"{k}={v}" for k, v in self.filters.items())
            desc += f" WHERE {filter_str}"
        if self.group_by:
            desc += f" GROUP BY {self.group_by}"
        if self.limit:
            desc += f" LIMIT {self.limit}"
        return desc


@dataclass
class CalculationResult:
    """Result of a calculation."""
    
    request: CalculationRequest
    value: Any  # The computed value (number, list, dict)
    sql_used: str  # The SQL that was executed (for auditing)
    row_count: int  # Number of rows involved
    
    def to_context_string(self) -> str:
        """Format result for inclusion in LLM context."""
        if isinstance(self.value, dict):
            # Group by result
            items = [f"  {k}: {v}" for k, v in self.value.items()]
            return f"{self.request.to_description()}:\n" + "\n".join(items)
        elif isinstance(self.value, list):
            # List result
            return f"{self.request.to_description()}: {', '.join(str(v) for v in self.value)}"
        else:
            # Scalar result
            return f"{self.request.to_description()} = {self.value}"


class SafeCalculator:
    """
    Executes calculations safely via SQL.
    
    This class provides a safe way for the LLM to request calculations
    without doing arithmetic itself. All operations are executed via
    parameterized SQL queries (preventing injection) on a read-only
    connection.
    """
    
    # Allowed columns for calculations (whitelist)
    ALLOWED_COLUMNS = {
        "stake_gbp", "price_delay_ms", "bet_id", "customer_id",
        "sport", "event_name", "market", "selection", "status", "incident_tag"
    }
    
    # Numeric columns (can be summed/averaged)
    NUMERIC_COLUMNS = {"stake_gbp", "price_delay_ms"}
    
    # Categorical columns (can be grouped/counted)
    CATEGORICAL_COLUMNS = {"sport", "status", "incident_tag", "customer_id", "market"}
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a read-only database connection."""
        # Open in read-only mode for safety
        conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _validate_column(self, column: str, must_be_numeric: bool = False) -> bool:
        """Validate that a column name is allowed."""
        if column not in self.ALLOWED_COLUMNS:
            raise ValueError(f"Column '{column}' is not allowed. Allowed: {self.ALLOWED_COLUMNS}")
        if must_be_numeric and column not in self.NUMERIC_COLUMNS:
            raise ValueError(f"Column '{column}' is not numeric. Numeric columns: {self.NUMERIC_COLUMNS}")
        return True
    
    def _build_where_clause(
        self, 
        filters: Optional[Dict[str, Any]]
    ) -> Tuple[str, List[Any]]:
        """
        Build a parameterized WHERE clause from filters.
        
        Returns (clause_string, params_list) for safe SQL construction.
        """
        if not filters:
            return "", []
        
        conditions = []
        params = []
        
        for column, value in filters.items():
            # Validate column name
            if column not in self.ALLOWED_COLUMNS:
                raise ValueError(f"Filter column '{column}' is not allowed")
            
            if isinstance(value, (list, tuple)):
                # IN clause
                placeholders = ", ".join("?" * len(value))
                conditions.append(f"{column} IN ({placeholders})")
                params.extend(value)
            elif isinstance(value, dict):
                # Range filters: {"gte": 100, "lte": 500}
                if "gte" in value:
                    conditions.append(f"{column} >= ?")
                    params.append(value["gte"])
                if "gt" in value:
                    conditions.append(f"{column} > ?")
                    params.append(value["gt"])
                if "lte" in value:
                    conditions.append(f"{column} <= ?")
                    params.append(value["lte"])
                if "lt" in value:
                    conditions.append(f"{column} < ?")
                    params.append(value["lt"])
            else:
                # Exact match
                conditions.append(f"{column} = ?")
                params.append(value)
        
        clause = " AND ".join(conditions)
        return f"WHERE {clause}" if clause else "", params
    
    def execute(self, request: CalculationRequest) -> CalculationResult:
        """
        Execute a calculation request safely.
        
        All calculations are performed via SQL with parameterized queries.
        """
        # Validate column
        needs_numeric = request.calc_type in {
            CalculationType.SUM, CalculationType.AVG, 
            CalculationType.MIN, CalculationType.MAX
        }
        if request.column != "*":
            self._validate_column(request.column, must_be_numeric=needs_numeric)
        
        # Build WHERE clause
        where_clause, params = self._build_where_clause(request.filters)
        
        # Execute based on calculation type
        if request.calc_type == CalculationType.SUM:
            return self._execute_aggregate("SUM", request, where_clause, params)
        elif request.calc_type == CalculationType.COUNT:
            return self._execute_aggregate("COUNT", request, where_clause, params)
        elif request.calc_type == CalculationType.AVG:
            return self._execute_aggregate("AVG", request, where_clause, params)
        elif request.calc_type == CalculationType.MIN:
            return self._execute_aggregate("MIN", request, where_clause, params)
        elif request.calc_type == CalculationType.MAX:
            return self._execute_aggregate("MAX", request, where_clause, params)
        elif request.calc_type == CalculationType.DISTINCT_COUNT:
            return self._execute_distinct_count(request, where_clause, params)
        elif request.calc_type == CalculationType.LIST:
            return self._execute_list(request, where_clause, params)
        elif request.calc_type == CalculationType.TOP_N:
            return self._execute_top_n(request, where_clause, params, desc=True)
        elif request.calc_type == CalculationType.BOTTOM_N:
            return self._execute_top_n(request, where_clause, params, desc=False)
        elif request.calc_type == CalculationType.GROUP_BY:
            return self._execute_group_by(request, where_clause, params)
        else:
            raise ValueError(f"Unknown calculation type: {request.calc_type}")
    
    def _execute_aggregate(
        self, 
        func: str, 
        request: CalculationRequest,
        where_clause: str,
        params: List[Any]
    ) -> CalculationResult:
        """Execute an aggregate function (SUM, COUNT, AVG, MIN, MAX)."""
        column = "*" if request.column == "*" else request.column
        sql = f"SELECT {func}({column}) as result, COUNT(*) as cnt FROM bets {where_clause}"
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            row = cursor.fetchone()
            
            value = row["result"]
            # Format monetary values
            if request.column == "stake_gbp" and value is not None:
                value = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            
            return CalculationResult(
                request=request,
                value=value,
                sql_used=sql,
                row_count=row["cnt"]
            )
    
    def _execute_distinct_count(
        self,
        request: CalculationRequest,
        where_clause: str,
        params: List[Any]
    ) -> CalculationResult:
        """Count distinct values in a column."""
        sql = f"SELECT COUNT(DISTINCT {request.column}) as result, COUNT(*) as cnt FROM bets {where_clause}"
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            row = cursor.fetchone()
            
            return CalculationResult(
                request=request,
                value=row["result"],
                sql_used=sql,
                row_count=row["cnt"]
            )
    
    def _execute_list(
        self,
        request: CalculationRequest,
        where_clause: str,
        params: List[Any]
    ) -> CalculationResult:
        """Get list of distinct values."""
        limit_clause = f"LIMIT {request.limit}" if request.limit else ""
        sql = f"SELECT DISTINCT {request.column} FROM bets {where_clause} ORDER BY {request.column} {limit_clause}"
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            values = [row[0] for row in cursor.fetchall()]
            
            # Get total count
            count_sql = f"SELECT COUNT(*) FROM bets {where_clause}"
            cursor.execute(count_sql, params)
            count = cursor.fetchone()[0]
            
            return CalculationResult(
                request=request,
                value=values,
                sql_used=sql,
                row_count=count
            )
    
    def _execute_top_n(
        self,
        request: CalculationRequest,
        where_clause: str,
        params: List[Any],
        desc: bool = True
    ) -> CalculationResult:
        """Get top/bottom N records by a column."""
        order = "DESC" if desc else "ASC"
        limit = request.limit or 5
        # Include all commonly needed columns, not just the sorted column
        sql = f"""
            SELECT bet_id, customer_id, stake_gbp, price_delay_ms, status, incident_tag
            FROM bets {where_clause}
            ORDER BY {request.column} {order}
            LIMIT {limit}
        """
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                results.append({
                    "bet_id": row["bet_id"],
                    "customer_id": row["customer_id"],
                    "stake_gbp": Decimal(str(row["stake_gbp"])).quantize(Decimal("0.01")),
                    "price_delay_ms": row["price_delay_ms"],
                    "status": row["status"],
                    "incident_tag": row["incident_tag"]
                })
            
            # Get total count
            count_sql = f"SELECT COUNT(*) FROM bets {where_clause}"
            cursor.execute(count_sql, params)
            count = cursor.fetchone()[0]
            
            return CalculationResult(
                request=request,
                value=results,
                sql_used=sql,
                row_count=count
            )
    
    def _execute_group_by(
        self,
        request: CalculationRequest,
        where_clause: str,
        params: List[Any]
    ) -> CalculationResult:
        """Group by a column and aggregate."""
        if not request.group_by:
            raise ValueError("GROUP_BY calculation requires group_by column")
        
        self._validate_column(request.group_by)
        
        # Determine aggregation
        if request.column in self.NUMERIC_COLUMNS:
            agg = f"SUM({request.column}) as total, AVG({request.column}) as avg, COUNT(*) as count"
        else:
            agg = "COUNT(*) as count"
        
        sql = f"""
            SELECT {request.group_by}, {agg}
            FROM bets {where_clause}
            GROUP BY {request.group_by}
            ORDER BY count DESC
        """
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            results = {}
            for row in rows:
                key = row[request.group_by]
                if request.column in self.NUMERIC_COLUMNS:
                    total = Decimal(str(row["total"])).quantize(Decimal("0.01")) if row["total"] else Decimal("0")
                    avg = Decimal(str(row["avg"])).quantize(Decimal("0.01")) if row["avg"] else Decimal("0")
                    results[key] = {
                        "count": row["count"],
                        "total": total,
                        "avg": avg
                    }
                else:
                    results[key] = row["count"]
            
            # Get total count
            count_sql = f"SELECT COUNT(*) FROM bets {where_clause}"
            cursor.execute(count_sql, params)
            count = cursor.fetchone()[0]
            
            return CalculationResult(
                request=request,
                value=results,
                sql_used=sql,
                row_count=count
            )
    
    # ==================== Convenience Methods ====================
    
    def sum_stake(self, **filters) -> CalculationResult:
        """Calculate total stake with optional filters."""
        return self.execute(CalculationRequest(
            calc_type=CalculationType.SUM,
            column="stake_gbp",
            filters=filters if filters else None
        ))
    
    def count_bets(self, **filters) -> CalculationResult:
        """Count bets with optional filters."""
        return self.execute(CalculationRequest(
            calc_type=CalculationType.COUNT,
            column="*",
            filters=filters if filters else None
        ))
    
    def avg_delay(self, **filters) -> CalculationResult:
        """Calculate average delay with optional filters."""
        return self.execute(CalculationRequest(
            calc_type=CalculationType.AVG,
            column="price_delay_ms",
            filters=filters if filters else None
        ))
    
    def top_by_stake(self, n: int = 5, **filters) -> CalculationResult:
        """Get top N bets by stake."""
        return self.execute(CalculationRequest(
            calc_type=CalculationType.TOP_N,
            column="stake_gbp",
            filters=filters if filters else None,
            limit=n
        ))
    
    def top_by_delay(self, n: int = 5, **filters) -> CalculationResult:
        """Get top N bets by delay."""
        return self.execute(CalculationRequest(
            calc_type=CalculationType.TOP_N,
            column="price_delay_ms",
            filters=filters if filters else None,
            limit=n
        ))
    
    def top_by_stake(self, n: int = 5, **filters) -> CalculationResult:
        """Get top N bets by stake."""
        return self.execute(CalculationRequest(
            calc_type=CalculationType.TOP_N,
            column="stake_gbp",
            filters=filters if filters else None,
            limit=n
        ))
    
    def group_by_status(self, column: str = "stake_gbp") -> CalculationResult:
        """Group by status and aggregate."""
        return self.execute(CalculationRequest(
            calc_type=CalculationType.GROUP_BY,
            column=column,
            group_by="status"
        ))
    
    def group_by_incident(self, column: str = "stake_gbp") -> CalculationResult:
        """Group by incident tag and aggregate."""
        return self.execute(CalculationRequest(
            calc_type=CalculationType.GROUP_BY,
            column=column,
            group_by="incident_tag"
        ))
    
    def customers_affected(self, **filters) -> CalculationResult:
        """Count distinct customers matching filters."""
        return self.execute(CalculationRequest(
            calc_type=CalculationType.DISTINCT_COUNT,
            column="customer_id",
            filters=filters if filters else None
        ))


def parse_calculation_request(text: str) -> Optional[CalculationRequest]:
    """
    Parse a calculation request from LLM output.
    
    Supports formats like:
    - CALC:SUM(stake_gbp WHERE status='SETTLED')
    - CALC:COUNT(* WHERE incident_tag='LATENCY_SPIKE')
    - CALC:TOP_5(price_delay_ms)
    - CALC:GROUP_BY(stake_gbp BY status)
    
    Returns None if no calculation request found.
    """
    # Look for CALC: prefix
    match = re.search(r'CALC:(\w+)\(([^)]+)\)', text)
    if not match:
        return None
    
    func = match.group(1).upper()
    args = match.group(2).strip()
    
    # Parse function type
    calc_type = None
    limit = None
    
    if func == "SUM":
        calc_type = CalculationType.SUM
    elif func == "COUNT":
        calc_type = CalculationType.COUNT
    elif func == "AVG":
        calc_type = CalculationType.AVG
    elif func == "MIN":
        calc_type = CalculationType.MIN
    elif func == "MAX":
        calc_type = CalculationType.MAX
    elif func.startswith("TOP_"):
        calc_type = CalculationType.TOP_N
        limit = int(func.split("_")[1])
    elif func.startswith("BOTTOM_"):
        calc_type = CalculationType.BOTTOM_N
        limit = int(func.split("_")[1])
    elif func == "GROUP_BY":
        calc_type = CalculationType.GROUP_BY
    elif func == "DISTINCT":
        calc_type = CalculationType.DISTINCT_COUNT
    else:
        return None
    
    # Parse column and filters
    column = "*"
    filters = None
    group_by = None
    
    # Check for WHERE clause
    if " WHERE " in args.upper():
        parts = re.split(r'\s+WHERE\s+', args, flags=re.IGNORECASE)
        column = parts[0].strip()
        filter_str = parts[1].strip()
        filters = _parse_filters(filter_str)
    # Check for BY clause (GROUP_BY)
    elif " BY " in args.upper():
        parts = re.split(r'\s+BY\s+', args, flags=re.IGNORECASE)
        column = parts[0].strip()
        group_by = parts[1].strip()
    else:
        column = args.strip()
    
    return CalculationRequest(
        calc_type=calc_type,
        column=column,
        filters=filters,
        group_by=group_by,
        limit=limit
    )


def _parse_filters(filter_str: str) -> Dict[str, Any]:
    """Parse a filter string like "status='SETTLED' AND incident_tag='NONE'"."""
    filters = {}
    
    # Split by AND
    conditions = re.split(r'\s+AND\s+', filter_str, flags=re.IGNORECASE)
    
    for condition in conditions:
        condition = condition.strip()
        
        # Match column='value' or column="value"
        match = re.match(r"(\w+)\s*=\s*['\"]?([^'\"]+)['\"]?", condition)
        if match:
            col = match.group(1)
            val = match.group(2)
            
            # Try to convert to number if applicable
            try:
                val = int(val)
            except ValueError:
                try:
                    val = float(val)
                except ValueError:
                    pass
            
            filters[col] = val
    
    return filters
