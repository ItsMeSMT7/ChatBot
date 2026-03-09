"""
Solven Analytics Engine v2.0 — Optimized 9-Phase Pipeline
With real-time phase tracking for frontend sync.
"""

import json
import pandas as pd
import numpy as np
import datetime
import traceback
import threading
import re
from django.db import connection
from api.ollama_service import generate_response, generate_embedding


# ═══════════════════════════════════════════════════
# PHASE TRACKER — Frontend polls this via API
# ═══════════════════════════════════════════════════

_phase_lock = threading.Lock()
_current_phase = {
    "phase": 0,
    "phase_name": "Waiting",
    "status": "idle",
    "detail": "",
}


def get_current_phase():
    """Called by analytics_views.py to return current phase to frontend."""
    with _phase_lock:
        return dict(_current_phase)


def _set_phase(phase_num, phase_name, detail=""):
    """Update the current phase (called internally during pipeline)."""
    with _phase_lock:
        _current_phase["phase"] = phase_num
        _current_phase["phase_name"] = phase_name
        _current_phase["status"] = "running"
        _current_phase["detail"] = detail
    print(f"[Phase {phase_num}/9] {phase_name}... {detail}")


def _set_complete():
    """Mark pipeline as complete."""
    with _phase_lock:
        _current_phase["phase"] = 9
        _current_phase["phase_name"] = "Complete"
        _current_phase["status"] = "complete"
        _current_phase["detail"] = ""


def _set_error(msg):
    """Mark pipeline as errored."""
    with _phase_lock:
        _current_phase["status"] = "error"
        _current_phase["detail"] = msg


# ═══════════════════════════════════════════════════
# UTILITY HELPERS
# ═══════════════════════════════════════════════════

def _safe_json_loads(json_str):
    """Parse JSON from LLM response."""
    if not json_str or not isinstance(json_str, str):
        return {}
    try:
        cleaned = json_str.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0]
        elif "```" in cleaned:
            parts = cleaned.split("```")
            if len(parts) >= 3:
                cleaned = parts[1]
                first_nl = cleaned.find('\n')
                if first_nl != -1 and first_nl < 20:
                    maybe_lang = cleaned[:first_nl].strip()
                    if maybe_lang.isalpha():
                        cleaned = cleaned[first_nl:]
        cleaned = cleaned.strip()
        return json.loads(cleaned)
    except json.JSONDecodeError:
        try:
            start_obj = cleaned.find('{')
            start_arr = cleaned.find('[')
            if start_obj == -1 and start_arr == -1:
                return {}
            if start_arr != -1 and (start_obj == -1 or start_arr < start_obj):
                start, open_c, close_c = start_arr, '[', ']'
            else:
                start, open_c, close_c = start_obj, '{', '}'
            depth = 0
            for i in range(start, len(cleaned)):
                if cleaned[i] == open_c:
                    depth += 1
                elif cleaned[i] == close_c:
                    depth -= 1
                if depth == 0:
                    return json.loads(cleaned[start:i + 1])
        except Exception:
            pass
        print(f"[JSON Parser] Failed. Preview: {json_str[:300]}")
        return {}
    except Exception as e:
        print(f"[JSON Parser] Error: {e}")
        return {}


def _llm_call(prompt, max_retries=2):
    """Call LLM with retry on failure."""
    for attempt in range(max_retries + 1):
        try:
            raw = generate_response(prompt)
            result = _safe_json_loads(raw)
            if result:
                return result
            if attempt < max_retries:
                print(f"[LLM] Empty on attempt {attempt+1}, retrying...")
                # Shorten the prompt on retry to avoid token limit
                prompt = prompt + "\n\nRESPOND WITH ONLY VALID JSON. NO MARKDOWN. NO EXPLANATION."
        except Exception as e:
            print(f"[LLM] Error attempt {attempt+1}: {e}")
    return {}


def _to_serializable(obj):
    """Convert numpy/pandas types to Python types."""
    if isinstance(obj, dict):
        return {k: _to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_to_serializable(v) for v in obj]
    elif isinstance(obj, (np.int64, np.int32, np.int16, np.int8)):
        return int(obj)
    elif isinstance(obj, (np.float64, np.float32, np.float16)):
        return float(obj) if not np.isnan(obj) else 0
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, (pd.Timestamp, datetime.datetime)):
        return obj.isoformat()
    elif isinstance(obj, pd.Series):
        return obj.tolist()
    elif pd.api.types.is_scalar(obj) and pd.isna(obj):
        return None
    return obj


# ═══════════════════════════════════════════════════
# DATA HELPERS
# ═══════════════════════════════════════════════════

def _build_profile(df):
    """Build statistical profile of DataFrame."""
    profile = {
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "columns": [],
        "numeric_stats": {},
        "categorical_stats": {},
        "temporal_detected": [],
        "sample_data": _to_serializable(
            df.head(3).fillna("NULL").to_dict(orient='records')
        ),
    }

    for col in df.columns:
        info = {
            "column_name": col,
            "pandas_dtype": str(df[col].dtype),
            "null_percentage": round(float(df[col].isnull().sum() / max(len(df), 1) * 100), 2),
            "unique_values": int(df[col].nunique()),
        }

        non_null = df[col].dropna()
        info["sample_values"] = [str(v) for v in non_null.head(3).tolist()] if len(non_null) > 0 else []

        if pd.api.types.is_numeric_dtype(df[col]):
            try:
                stats = {
                    "sum": float(df[col].sum()) if pd.notnull(df[col].sum()) else 0,
                    "mean": round(float(df[col].mean()), 2) if pd.notnull(df[col].mean()) else 0,
                    "min": float(df[col].min()) if pd.notnull(df[col].min()) else 0,
                    "max": float(df[col].max()) if pd.notnull(df[col].max()) else 0,
                    "count": int(df[col].count()),
                }
                info["is_numeric"] = True
                profile["numeric_stats"][col] = stats
            except Exception:
                info["is_numeric"] = False
        else:
            info["is_numeric"] = False

        if df[col].dtype == 'object' or df[col].dtype.name == 'category':
            try:
                vc = df[col].value_counts().head(8)
                info["top_values"] = {str(k): int(v) for k, v in vc.items()}
                info["is_categorical"] = True
                profile["categorical_stats"][col] = info["top_values"]
            except Exception:
                info["is_categorical"] = False
        else:
            info["is_categorical"] = False

        info["is_temporal"] = False
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            info["is_temporal"] = True
            profile["temporal_detected"].append(col)
        elif df[col].dtype == 'object':
            try:
                sample = df[col].dropna().head(20)
                parsed = pd.to_datetime(sample, infer_datetime_format=True, errors='coerce')
                if parsed.notna().sum() >= len(sample) * 0.7:
                    info["is_temporal"] = True
                    profile["temporal_detected"].append(col)
            except Exception:
                pass

        profile["columns"].append(info)

    return _to_serializable(profile)


def _find_column(name, df):
    """Find the best matching column in DataFrame."""
    if not name:
        return None
    if name in df.columns:
        return name
    for col in df.columns:
        if col.lower() == name.lower():
            return col
    for col in df.columns:
        if name.lower() in col.lower() or col.lower() in name.lower():
            return col
    clean_name = name.lower().replace(" ", "").replace("_", "").replace("-", "")
    for col in df.columns:
        clean_col = col.lower().replace(" ", "").replace("_", "").replace("-", "")
        if clean_name == clean_col:
            return col
    return None


def _compute_kpi_value(df, kpi_spec):
    """Compute KPI value using Pandas with fuzzy column matching."""
    try:
        formula = kpi_spec.get("formula", "").lower()
        columns_used = kpi_spec.get("columns_used", [])

        valid_cols = []
        for col_name in columns_used:
            matched = _find_column(col_name, df)
            if matched:
                valid_cols.append(matched)

        if not valid_cols:
            for real_col in df.columns:
                if pd.api.types.is_numeric_dtype(df[real_col]):
                    if real_col.lower() in formula:
                        valid_cols.append(real_col)

        if not valid_cols:
            return None

        if ("*" in formula or "x" in formula) and "sum" in formula:
            if len(valid_cols) >= 2:
                c1, c2 = valid_cols[0], valid_cols[1]
                if pd.api.types.is_numeric_dtype(df[c1]) and pd.api.types.is_numeric_dtype(df[c2]):
                    return float((df[c1] * df[c2]).sum())

        if any(w in formula for w in ["ratio", "%", "margin", "percentage", "/"]):
            if len(valid_cols) >= 2:
                if pd.api.types.is_numeric_dtype(df[valid_cols[0]]) and pd.api.types.is_numeric_dtype(df[valid_cols[1]]):
                    denom = df[valid_cols[1]].sum()
                    if denom and denom != 0:
                        return round(float(df[valid_cols[0]].sum() / denom * 100), 2)

        if "sum" in formula and pd.api.types.is_numeric_dtype(df[valid_cols[0]]):
            return float(df[valid_cols[0]].sum())

        if any(w in formula for w in ["avg", "average", "mean"]):
            if pd.api.types.is_numeric_dtype(df[valid_cols[0]]):
                return round(float(df[valid_cols[0]].mean()), 2)

        if "distinct" in formula or "unique" in formula:
            return int(df[valid_cols[0]].nunique())

        if "count" in formula:
            return int(df[valid_cols[0]].count())

        if "max" in formula or "highest" in formula:
            if pd.api.types.is_numeric_dtype(df[valid_cols[0]]):
                return float(df[valid_cols[0]].max())

        if "min" in formula or "lowest" in formula:
            if pd.api.types.is_numeric_dtype(df[valid_cols[0]]):
                return float(df[valid_cols[0]].min())

        if "-" in formula and len(valid_cols) >= 2:
            if pd.api.types.is_numeric_dtype(df[valid_cols[0]]) and pd.api.types.is_numeric_dtype(df[valid_cols[1]]):
                return float(df[valid_cols[0]].sum() - df[valid_cols[1]].sum())

        if pd.api.types.is_numeric_dtype(df[valid_cols[0]]):
            return float(df[valid_cols[0]].sum())

        return None
    except Exception as e:
        print(f"[KPI Compute] Error: {e}")
        return None


def _safe_value(value):
    """Ensure value is not NaN/Inf before using it."""
    if value is None:
        return None
    try:
        if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
            return None
    except (TypeError, ValueError):
        return None
    return value


def _format_kpi_value(value, kpi_name=""):
    """Format numeric value for display. Handles NaN safely."""
    # ── Handle None, NaN, and invalid values ──
    if value is None:
        return "N/A"

    try:
        # Check for NaN (works for float NaN)
        if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
            return "N/A"
    except (TypeError, ValueError):
        return "N/A"

    try:
        # Convert to float safely
        value = float(value)
    except (TypeError, ValueError):
        return str(value)

    # ── Check again after conversion ──
    if np.isnan(value) or np.isinf(value):
        return "N/A"

    name_lower = kpi_name.lower()

    # Percentage
    if any(w in name_lower for w in ['rate', 'margin', 'percentage', 'ratio', '%', 'share']):
        return f"{value:.2f}%"

    # Currency
    if any(w in name_lower for w in ['revenue', 'profit', 'cost', 'price', 'sales', 'income', 'expense', 'value', 'spend', 'amount']):
        if abs(value) >= 1_000_000_000:
            return f"${value / 1_000_000_000:,.2f}B"
        if abs(value) >= 1_000_000:
            return f"${value / 1_000_000:,.2f}M"
        if abs(value) >= 1_000:
            return f"${value:,.2f}"
        return f"${value:.2f}"

    # Count
    if any(w in name_lower for w in ['count', 'total', 'number', 'orders', 'customers', 'transactions']):
        try:
            return f"{int(value):,}"
        except (ValueError, OverflowError):
            return f"{value:,.0f}"

    # General number
    if isinstance(value, float):
        try:
            if abs(value) < 1e15 and value == int(value):
                return f"{int(value):,}"
        except (ValueError, OverflowError):
            pass
        return f"{value:,.2f}"

    return str(value)

def _generate_chart_data(df, chart_spec):
    """Execute Pandas aggregation for chart data."""
    try:
        raw_x = chart_spec.get("x_axis", {}).get("column", "")
        raw_y = chart_spec.get("y_axis", {}).get("column", "")
        aggregation = chart_spec.get("y_axis", {}).get("aggregation", "SUM").upper()
        chart_type = chart_spec.get("chart_type", "").lower()
        sort_order = chart_spec.get("sort_order", "")

        x_col = _find_column(raw_x, df)
        y_col = _find_column(raw_y, df)

        print(f"    x: '{raw_x}' -> '{x_col}' | y: '{raw_y}' -> '{y_col}' | type: {chart_type}")

        # SCATTER
        if chart_type == "scatter":
            if x_col and y_col and x_col in df.columns and y_col in df.columns:
                scatter = df[[x_col, y_col]].dropna()
                if pd.api.types.is_numeric_dtype(scatter[x_col]) and pd.api.types.is_numeric_dtype(scatter[y_col]):
                    return _to_serializable(
                        [{"x": row[x_col], "y": row[y_col]} for _, row in scatter.head(150).iterrows()]
                    )
            num_cols = df.select_dtypes(include=['number']).columns.tolist()
            if len(num_cols) >= 2:
                scatter = df[[num_cols[0], num_cols[1]]].dropna().head(150)
                return _to_serializable(
                    [{"x": row[num_cols[0]], "y": row[num_cols[1]]} for _, row in scatter.iterrows()]
                )
            return []

        # HISTOGRAM
        if chart_type == "histogram":
            target = x_col if x_col and x_col in df.columns else y_col
            if target and target in df.columns and pd.api.types.is_numeric_dtype(df[target]):
                counts, edges = np.histogram(df[target].dropna(), bins=10)
                return [{"name": f"{edges[i]:.1f}-{edges[i+1]:.1f}", "value": int(counts[i])} for i in range(len(counts))]
            num_cols = df.select_dtypes(include=['number']).columns.tolist()
            if num_cols:
                counts, edges = np.histogram(df[num_cols[0]].dropna(), bins=10)
                return [{"name": f"{edges[i]:.1f}-{edges[i+1]:.1f}", "value": int(counts[i])} for i in range(len(counts))]
            return []

        # STANDARD CHARTS
        grouped = None

        if x_col and y_col and x_col in df.columns and y_col in df.columns:
            if pd.api.types.is_numeric_dtype(df[y_col]):
                agg_map = {"SUM": "sum", "AVG": "mean", "MEAN": "mean", "AVERAGE": "mean",
                           "COUNT": "count", "MAX": "max", "MIN": "min", "MEDIAN": "median"}
                agg_func = agg_map.get(aggregation, "sum")
                grouped = df.groupby(x_col)[y_col].agg(agg_func).reset_index()
                grouped.columns = ['name', 'value']
            else:
                grouped = df.groupby(x_col).size().reset_index(name='value')
                grouped = grouped.rename(columns={x_col: 'name'})
        elif x_col and x_col in df.columns:
            num_cols = df.select_dtypes(include=['number']).columns.tolist()
            if num_cols:
                grouped = df.groupby(x_col)[num_cols[0]].sum().reset_index()
                grouped.columns = ['name', 'value']
            else:
                grouped = df[x_col].value_counts().reset_index()
                grouped.columns = ['name', 'value']
        elif y_col and y_col in df.columns and pd.api.types.is_numeric_dtype(df[y_col]):
            cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
            if cat_cols:
                grouped = df.groupby(cat_cols[0])[y_col].sum().reset_index()
                grouped.columns = ['name', 'value']
        else:
            cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
            num_cols = df.select_dtypes(include=['number']).columns.tolist()
            if cat_cols and num_cols:
                grouped = df.groupby(cat_cols[0])[num_cols[0]].sum().reset_index()
                grouped.columns = ['name', 'value']
            elif cat_cols:
                grouped = df[cat_cols[0]].value_counts().reset_index()
                grouped.columns = ['name', 'value']
            elif num_cols:
                counts, edges = np.histogram(df[num_cols[0]].dropna(), bins=10)
                return [{"name": f"{edges[i]:.1f}-{edges[i+1]:.1f}", "value": int(counts[i])} for i in range(len(counts))]
            else:
                return []

        if grouped is None:
            return []

        if sort_order == "descending":
            grouped = grouped.sort_values('value', ascending=False)
        elif sort_order == "ascending":
            grouped = grouped.sort_values('value', ascending=True)

        grouped['name'] = grouped['name'].astype(str)
        if pd.api.types.is_numeric_dtype(grouped['value']):
            grouped['value'] = grouped['value'].round(2)

        return _to_serializable(grouped.head(15).to_dict(orient='records'))

    except Exception as e:
        print(f"    [Chart Data] Error: {e}")
        return []


# ═══════════════════════════════════════════════════
# PHASE 1
# ═══════════════════════════════════════════════════

def _phase_1(df):
    """Phase 1: Schema analysis."""
    profile = _build_profile(df)

    # SHORTER prompt to avoid token limit
    # Only send first 10 columns if too many
    cols_to_send = profile['columns'][:15]

    prompt = f"""Classify these dataset columns. Rows: {profile['total_rows']}, Cols: {profile['total_columns']}

Columns: {json.dumps(cols_to_send, indent=1)}

Sample: {json.dumps(profile['sample_data'][:2], indent=1)}

Classify each as: metric, dimension, temporal, or identifier.
Respond ONLY with JSON:
{{
  "dataset_profile": {{
    "total_rows": {profile['total_rows']},
    "total_columns": {profile['total_columns']},
    "domain": "domain name",
    "data_quality_score": "85%",
    "columns": [
      {{"column_name": "name", "data_type": "type", "classification": "metric|dimension|temporal|identifier", "business_meaning": "desc", "null_percentage": 0, "unique_values": 0, "sample_values": []}}
    ],
    "column_classifications": {{
      "metrics": [], "dimensions": [], "temporal": [], "identifiers": []
    }}
  }}
}}"""

    result = _llm_call(prompt)
    if result:
        result["_numeric_stats"] = profile.get("numeric_stats", {})
        result["_categorical_stats"] = profile.get("categorical_stats", {})
        result["_all_columns"] = [c["column_name"] for c in profile["columns"]]
        result["_temporal_detected"] = profile.get("temporal_detected", [])
    return result


# ═══════════════════════════════════════════════════
# PHASE 2+3 COMBINED
# ═══════════════════════════════════════════════════

def _phase_2_3_combined(profile_data, numeric_stats):
    """Phase 2+3: Generate AND select top 5 KPIs with EXACT column names."""
    dp = profile_data.get("dataset_profile", {})

    # Build explicit column list with types
    col_desc = "EXACT COLUMN NAMES IN DATASET:\n"
    for col in dp.get("columns", [])[:20]:
        col_name = col.get('column_name', '?')
        col_class = col.get('classification', '?').upper()
        col_desc += f'  - "{col_name}" [{col_class}]'
        # Add stats if numeric
        if col_name in numeric_stats:
            s = numeric_stats[col_name]
            col_desc += f' sum={s.get("sum",0)}, mean={s.get("mean",0)}, min={s.get("min",0)}, max={s.get("max",0)}, count={s.get("count",0)}'
        col_desc += "\n"

    numeric_stats_json = json.dumps(numeric_stats, indent=1, default=str)
    categorical_json = json.dumps(profile_data.get('_categorical_stats', {}), indent=1, default=str)

    prompt = f"""You are a Business Analytics Engine. Generate TOP 5 KPIs.

{col_desc}

NUMERIC STATS: {numeric_stats_json}

CATEGORY VALUES: {categorical_json}

RULES:
1. In "columns_used", you MUST use the EXACT column names shown above in quotes
2. Do NOT rename or modify column names
3. Use formulas that can be computed: SUM, AVG, COUNT, MAX, MIN, DISTINCT
4. For formulas with 2 columns, BOTH must exist in the dataset
5. Generate exactly 5 KPIs

Respond ONLY with JSON:
{{
  "selected_kpis": [
    {{
      "kpi_name": "descriptive name",
      "category": "FINANCIAL|OPERATIONAL|GROWTH|CUSTOMER|PERFORMANCE",
      "business_meaning": "what it measures",
      "formula": "e.g. SUM(Price) or AVG(Quantity) or COUNT(DISTINCT(Customer))",
      "columns_used": ["exact_column_name_from_above"],
      "strategic_importance": "why it matters",
      "priority_score": 90
    }}
  ]
}}"""

    return _llm_call(prompt)


# ═══════════════════════════════════════════════════
# PHASE 4
# ═══════════════════════════════════════════════════

def _phase_4(selected_kpis, numeric_stats, df_columns):
    """Phase 4: Formula engineering."""
    kpis_json = json.dumps(selected_kpis.get('selected_kpis', []), indent=1, default=str)
    columns_json = json.dumps(df_columns, default=str)
    stats_json = json.dumps(numeric_stats, indent=1, default=str)

    prompt = f"""Define computation for these KPIs.

KPIs: {kpis_json}

COLUMNS: {columns_json}
STATS: {stats_json}

Use ONLY columns from COLUMNS. Respond ONLY with JSON:
{{
  "kpis": [
    {{
      "kpi_id": "KPI-001",
      "kpi_name": "name",
      "formula": "SUM(ColumnName)",
      "columns_used": ["ExactColumnName"],
      "computation_method": {{
        "python": "df['Col'].sum()",
        "sql": "SELECT SUM(Col) FROM data"
      }},
      "trend_direction": "up|down|stable",
      "strategic_priority": "HIGH|MEDIUM|LOW",
      "business_insight": "insight",
      "actionable_recommendation": "action"
    }}
  ]
}}"""

    return _llm_call(prompt)


# ═══════════════════════════════════════════════════
# PHASE 5
# ═══════════════════════════════════════════════════
def _phase_5(kpi_specs, df, numeric_stats):
    """Phase 5: Compute KPI values with Pandas. Accurate computation."""
    computed = []
    all_numeric_cols = list(df.select_dtypes(include=['number']).columns)
    all_cat_cols = list(df.select_dtypes(include=['object', 'category']).columns)

    for idx, kpi in enumerate(kpi_specs.get("kpis", [])):
        value = None
        formula = kpi.get("formula", "").lower()
        columns_used = kpi.get("columns_used", [])

        # Step 1: Resolve actual column names
        resolved_cols = []
        for col_name in columns_used:
            matched = _find_column(col_name, df)
            if matched:
                resolved_cols.append(matched)

        # Step 2: Try direct formula computation
        if resolved_cols:
            try:
                first_col = resolved_cols[0]

                # MULTIPLICATION + SUM: SUM(A * B)
                if len(resolved_cols) >= 2 and any(op in formula for op in ["*", "×", "multiply"]):
                    c1, c2 = resolved_cols[0], resolved_cols[1]
                    if pd.api.types.is_numeric_dtype(df[c1]) and pd.api.types.is_numeric_dtype(df[c2]):
                        if "avg" in formula or "mean" in formula or "average" in formula:
                            value = round(float((df[c1] * df[c2]).mean()), 2)
                        else:
                            value = float((df[c1] * df[c2]).sum())

                # RATIO / DIVISION: A / B
                elif len(resolved_cols) >= 2 and any(op in formula for op in ["/", "ratio", "margin", "percentage", "%"]):
                    c1, c2 = resolved_cols[0], resolved_cols[1]
                    if pd.api.types.is_numeric_dtype(df[c1]) and pd.api.types.is_numeric_dtype(df[c2]):
                        denom = df[c2].sum()
                        if denom != 0:
                            value = round(float(df[c1].sum() / denom * 100), 2)

                # SUBTRACTION: A - B
                elif len(resolved_cols) >= 2 and "-" in formula and "sub" not in formula:
                    c1, c2 = resolved_cols[0], resolved_cols[1]
                    if pd.api.types.is_numeric_dtype(df[c1]) and pd.api.types.is_numeric_dtype(df[c2]):
                        value = float(df[c1].sum() - df[c2].sum())

                # COUNT DISTINCT
                elif "distinct" in formula or "unique" in formula:
                    value = int(df[first_col].nunique())

                # COUNT
                elif "count" in formula and "distinct" not in formula:
                    value = int(df[first_col].count())

                # AVG / MEAN
                elif any(w in formula for w in ["avg", "average", "mean"]):
                    if pd.api.types.is_numeric_dtype(df[first_col]):
                        value = round(float(df[first_col].mean()), 2)

                # MAX
                elif any(w in formula for w in ["max", "highest", "maximum"]):
                    if pd.api.types.is_numeric_dtype(df[first_col]):
                        value = float(df[first_col].max())

                # MIN
                elif any(w in formula for w in ["min", "lowest", "minimum"]):
                    if pd.api.types.is_numeric_dtype(df[first_col]):
                        value = float(df[first_col].min())

                # SUM (default for numeric)
                elif "sum" in formula or "total" in formula:
                    if pd.api.types.is_numeric_dtype(df[first_col]):
                        value = float(df[first_col].sum())

                # MEDIAN
                elif "median" in formula:
                    if pd.api.types.is_numeric_dtype(df[first_col]):
                        value = float(df[first_col].median())

                # Fallback: if numeric column, do SUM
                elif pd.api.types.is_numeric_dtype(df[first_col]):
                    value = float(df[first_col].sum())

            except Exception as e:
                print(f"  [KPI Compute] Error for '{kpi.get('kpi_name', '?')}': {e}")

        # Step 3: Fallback using numeric_stats
        if value is None:
            for col_name in columns_used:
                for stat_key in numeric_stats:
                    if (stat_key.lower() == col_name.lower() or
                        col_name.lower() in stat_key.lower() or
                        stat_key.lower() in col_name.lower()):
                        s = numeric_stats[stat_key]
                        if any(w in formula for w in ["avg", "mean", "average"]):
                            value = s.get("mean")
                        elif any(w in formula for w in ["max", "highest"]):
                            value = s.get("max")
                        elif any(w in formula for w in ["min", "lowest"]):
                            value = s.get("min")
                        elif "count" in formula:
                            value = s.get("count")
                        else:
                            value = s.get("sum")
                        if value is not None:
                            break
                if value is not None:
                    break

        # Step 4: Last resort using KPI name
        if value is None:
            kpi_name_lower = kpi.get("kpi_name", "").lower()
            if any(w in kpi_name_lower for w in ["count", "number of", "total transactions", "total orders", "total records"]):
                value = len(df)
            elif any(w in kpi_name_lower for w in ["unique", "distinct"]):
                if all_cat_cols:
                    value = int(df[all_cat_cols[0]].nunique())
                elif all_numeric_cols:
                    value = int(df[all_numeric_cols[0]].nunique())
            elif all_numeric_cols:
                if any(w in kpi_name_lower for w in ["average", "avg", "mean"]):
                    value = round(float(df[all_numeric_cols[0]].mean()), 2)
                elif any(w in kpi_name_lower for w in ["max", "highest", "peak", "top"]):
                    value = float(df[all_numeric_cols[0]].max())
                elif any(w in kpi_name_lower for w in ["min", "lowest", "bottom"]):
                    value = float(df[all_numeric_cols[0]].min())
                else:
                    value = float(df[all_numeric_cols[0]].sum())

        value = _safe_value(value)
        name = kpi.get("kpi_name", f"KPI {idx+1}")
        computed.append({
            "kpi_id": kpi.get("kpi_id", f"KPI-{idx+1:03d}"),
            "kpi_name": name,
            "kpi_value": _format_kpi_value(value, name),
            "kpi_value_raw": value if value is not None else 0,
            "trend_direction": kpi.get("trend_direction", "stable"),
            "formula": kpi.get("formula", ""),
            "columns_used": kpi.get("columns_used", []),
            "computation_method": kpi.get("computation_method", {}),
            "business_insight": kpi.get("business_insight", ""),
            "actionable_recommendation": kpi.get("actionable_recommendation", ""),
            "strategic_priority": kpi.get("strategic_priority", "MEDIUM"),
        })

    return {"kpis": computed[:5]}

# ═══════════════════════════════════════════════════
# PHASE 6+7 COMBINED
# ═══════════════════════════════════════════════════

def _phase_6_7_combined(profile_data, computed_kpis):
    """Phase 6+7: Generate AND select top 6 charts."""
    dp = profile_data.get("dataset_profile", {})
    classifications = dp.get("column_classifications", {})

    metrics_json = json.dumps(classifications.get('metrics', []), default=str)
    dimensions_json = json.dumps(classifications.get('dimensions', []), default=str)
    temporal_json = json.dumps(classifications.get('temporal', []), default=str)

    kpi_list = []
    for k in computed_kpis.get("kpis", []):
        kpi_list.append({"name": k.get("kpi_name", ""), "value": k.get("kpi_value", "N/A")})
    kpis_json = json.dumps(kpi_list, indent=1, default=str)

    prompt = f"""Select 6 charts for a dashboard.

METRICS: {metrics_json}
DIMENSIONS: {dimensions_json}
TEMPORAL: {temporal_json}
KPIs: {kpis_json}

Types: bar, line, pie, donut, area, scatter, histogram
Include variety: 1 line/area, 1 bar, 1 pie/donut, 1 scatter/histogram.
Use ONLY column names from METRICS, DIMENSIONS, TEMPORAL.

Respond ONLY with JSON:
{{
  "charts": [
    {{
      "chart_id": "CHART-001",
      "chart_type": "bar",
      "title": "Title",
      "x_axis": {{"column": "ExactCol", "label": "Label"}},
      "y_axis": {{"column": "ExactCol", "label": "Label", "aggregation": "SUM"}},
      "group_by": null,
      "sort_order": "descending",
      "business_insight": "insight",
      "actionable_recommendation": "action"
    }}
  ]
}}"""

    return _llm_call(prompt)


# ═══════════════════════════════════════════════════
# PHASE 8
# ═══════════════════════════════════════════════════

def _phase_8(df, charts_spec):
    """Phase 8: Generate chart data with Pandas."""
    charts = charts_spec.get("charts", [])

    for chart in charts:
        chart["data"] = _generate_chart_data(df, chart)

        if not chart["data"]:
            print(f"  [Phase 8] Fallback for: {chart.get('title', '?')}")
            chart_type = chart.get("chart_type", "").lower()
            cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
            num_cols = df.select_dtypes(include=['number']).columns.tolist()

            try:
                if chart_type in ["pie", "donut"] and cat_cols:
                    vc = df[cat_cols[0]].value_counts().head(8).reset_index()
                    vc.columns = ['name', 'value']
                    vc['name'] = vc['name'].astype(str)
                    chart["data"] = _to_serializable(vc.to_dict(orient='records'))

                elif chart_type in ["line", "area"] and num_cols:
                    series = df[num_cols[0]].dropna().head(30).reset_index()
                    series.columns = ['name', 'value']
                    series['name'] = series['name'].astype(str)
                    chart["data"] = _to_serializable(series.to_dict(orient='records'))

                elif chart_type == "histogram" and num_cols:
                    counts, edges = np.histogram(df[num_cols[0]].dropna(), bins=10)
                    chart["data"] = [{"name": f"{edges[i]:.1f}-{edges[i+1]:.1f}", "value": int(counts[i])} for i in range(len(counts))]

                elif chart_type == "scatter" and len(num_cols) >= 2:
                    scatter = df[[num_cols[0], num_cols[1]]].dropna().head(100)
                    chart["data"] = _to_serializable([{"x": row[num_cols[0]], "y": row[num_cols[1]]} for _, row in scatter.iterrows()])

                elif cat_cols and num_cols:
                    grouped = df.groupby(cat_cols[0])[num_cols[0]].sum().reset_index()
                    grouped.columns = ['name', 'value']
                    grouped = grouped.sort_values('value', ascending=False).head(10)
                    grouped['name'] = grouped['name'].astype(str)
                    chart["data"] = _to_serializable(grouped.to_dict(orient='records'))

                elif cat_cols:
                    vc = df[cat_cols[0]].value_counts().head(10).reset_index()
                    vc.columns = ['name', 'value']
                    vc['name'] = vc['name'].astype(str)
                    chart["data"] = _to_serializable(vc.to_dict(orient='records'))

            except Exception as e:
                print(f"  [Phase 8] Fallback failed: {e}")
                chart["data"] = []

    charts_spec["charts"] = [c for c in charts if c.get("data")]
    charts_spec["charts"] = charts_spec["charts"][:6]
    return charts_spec


# ═══════════════════════════════════════════════════
# PHASE 9
# ═══════════════════════════════════════════════════

def _phase_9(profile_data, computed_kpis, charts_with_data, df):
    """Phase 9: Assemble final output."""
    dp = profile_data.get("dataset_profile", {})

    insights = []
    for idx, kpi in enumerate(computed_kpis.get("kpis", [])):
        if kpi.get("business_insight"):
            insights.append({
                "insight_id": f"INS-{idx+1:03d}",
                "insight": kpi["business_insight"],
                "impact_level": kpi.get("strategic_priority", "MEDIUM"),
                "recommended_action": kpi.get("actionable_recommendation", "Review this metric regularly.")
            })

    for chart in charts_with_data.get("charts", []):
        if chart.get("business_insight") and len(insights) < 6:
            insights.append({
                "insight_id": f"INS-{len(insights)+1:03d}",
                "insight": chart["business_insight"],
                "impact_level": "MEDIUM",
                "recommended_action": chart.get("actionable_recommendation", "Monitor this trend.")
            })

    kpi_summaries = [f"{k['kpi_name']}: {k['kpi_value']}" for k in computed_kpis.get("kpis", [])[:3]]
    executive_summary = (
        f"Analysis of {dp.get('total_rows', 0):,} records in the {dp.get('domain', 'business')} domain. "
        f"Key metrics: {', '.join(kpi_summaries)}. "
        f"{len(charts_with_data.get('charts', []))} visualizations generated."
    )

    date_range = ""
    for col in profile_data.get("_temporal_detected", []):
        if col in df.columns:
            try:
                dates = pd.to_datetime(df[col], errors='coerce').dropna()
                if len(dates) > 0:
                    date_range = f"{dates.min().strftime('%Y-%m-%d')} to {dates.max().strftime('%Y-%m-%d')}"
                    break
            except Exception:
                pass

    quality_notes = []
    for col_info in dp.get("columns", []):
        null_pct = col_info.get("null_percentage", 0)
        if isinstance(null_pct, (int, float)) and null_pct > 5:
            quality_notes.append(f"Column '{col_info['column_name']}' has {null_pct}% missing values.")
    if not quality_notes:
        quality_notes.append("Data quality is good.")

    return _to_serializable({
        "solven_analytics_output": {
            "version": "2.0",
            "analysis_timestamp": datetime.datetime.now().isoformat(),
            "dataset_summary": {
                "total_rows": dp.get("total_rows", len(df)),
                "total_columns": dp.get("total_columns", len(df.columns)),
                "domain": dp.get("domain", "General"),
                "date_range": date_range,
                "data_quality_score": dp.get("data_quality_score", "N/A"),
                "column_classifications": dp.get("column_classifications", {}),
            },
            "kpis": computed_kpis.get("kpis", []),
            "charts": charts_with_data.get("charts", []),
            "key_business_insights": insights[:5],
            "executive_summary": executive_summary,
            "data_quality_notes": quality_notes,
        }
    })


# ═══════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════

def run_solven_analytics_pipeline(dataset_path):
    """Main entry point called by analytics_views.py."""
    try:
        _set_phase(0, "Starting", "Loading data...")

        # Load
        if dataset_path.endswith('.csv'):
            try:
                df = pd.read_csv(dataset_path, encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(dataset_path, encoding="latin1")
        elif dataset_path.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(dataset_path)
        else:
            _set_error("Unsupported file format")
            return {"error": "Unsupported file format. Upload CSV or Excel."}

        if df.empty:
            _set_error("Empty file")
            return {"error": "The uploaded file contains no data."}

        df.columns = df.columns.str.strip()
        print(f"[Data] {len(df)} rows x {len(df.columns)} columns")

        numeric_stats = {}
        for col in df.select_dtypes(include=['number']).columns:
            try:
                numeric_stats[col] = {
                    "sum": float(df[col].sum()) if pd.notnull(df[col].sum()) else 0,
                    "mean": round(float(df[col].mean()), 2) if pd.notnull(df[col].mean()) else 0,
                    "min": float(df[col].min()) if pd.notnull(df[col].min()) else 0,
                    "max": float(df[col].max()) if pd.notnull(df[col].max()) else 0,
                    "count": int(df[col].count()),
                }
            except Exception:
                pass

        df_columns = list(df.columns)

        # PHASE 1
        _set_phase(1, "Data Profiling", "LLM Call 1/4")
        profile_data = _phase_1(df)
        if not profile_data or "dataset_profile" not in profile_data:
            print("[Phase 1] Using fallback profile")
            profile_data = {
                "dataset_profile": {
                    "total_rows": len(df), "total_columns": len(df.columns),
                    "domain": "General", "data_quality_score": "N/A",
                    "columns": [
                        {"column_name": c,
                         "classification": "metric" if pd.api.types.is_numeric_dtype(df[c]) else "dimension",
                         "null_percentage": round(float(df[c].isnull().sum() / len(df) * 100), 2)}
                        for c in df.columns
                    ],
                    "column_classifications": {
                        "metrics": list(df.select_dtypes(include=['number']).columns),
                        "dimensions": list(df.select_dtypes(include=['object', 'category']).columns),
                        "temporal": [], "identifiers": [],
                    }
                },
                "_numeric_stats": numeric_stats, "_categorical_stats": {},
                "_all_columns": df_columns, "_temporal_detected": [],
            }
        print("[Phase 1] Done")

        # PHASE 2+3
        _set_phase(2, "KPI Generation", "LLM Call 2/4")
        selected_kpis = _phase_2_3_combined(profile_data, numeric_stats)
        if not selected_kpis or not selected_kpis.get("selected_kpis"):
            _set_error("Could not generate KPIs")
            return {"error": "Could not generate KPIs from this dataset."}
        _set_phase(3, "KPI Prioritization", "Selected top 5")
        print(f"[Phase 2-3] Selected {len(selected_kpis['selected_kpis'])} KPIs")

        # PHASE 4
        _set_phase(4, "Formula Engineering", "LLM Call 3/4")
        kpi_formulas = _phase_4(selected_kpis, numeric_stats, df_columns)
        if not kpi_formulas or not kpi_formulas.get("kpis"):
            _set_error("Could not engineer formulas")
            return {"error": "Could not engineer KPI formulas."}
        print("[Phase 4] Done")

        # PHASE 5
        _set_phase(5, "KPI Computation", "Computing with Pandas")
        computed_kpis = _phase_5(kpi_formulas, df, numeric_stats)
        for kpi in computed_kpis.get("kpis", []):
            print(f"  -> {kpi['kpi_name']}: {kpi['kpi_value']}")
        print("[Phase 5] Done")

        # PHASE 6+7
        _set_phase(6, "Chart Ideation", "LLM Call 4/4")
        selected_charts = _phase_6_7_combined(profile_data, computed_kpis)
        if not selected_charts or not selected_charts.get("charts"):
            _set_error("Could not generate charts")
            return {"error": "Could not generate charts."}
        _set_phase(7, "Chart Selection", "Selected top 6")
        print(f"[Phase 6-7] Selected {len(selected_charts['charts'])} charts")

        # PHASE 8
        _set_phase(8, "Chart Data Generation", "Aggregating with Pandas")
        charts_with_data = _phase_8(df, selected_charts)
        for chart in charts_with_data.get("charts", []):
            print(f"  -> {chart.get('title', '?')}: {len(chart.get('data', []))} points")
        print("[Phase 8] Done")

        # PHASE 9
        _set_phase(9, "Final Consolidation", "Assembling output")
        final = _phase_9(profile_data, computed_kpis, charts_with_data, df)
        _set_complete()

        print("\n[Solven Analytics v2.0] Pipeline Complete!")
        return final

    except Exception as e:
        print(f"\n[ERROR] {e}")
        traceback.print_exc()
        _set_error(str(e))
        return {"error": f"Pipeline failed: {str(e)}"}



# ===================================================================
# ANALYTICS MAIN ENTRY POINT
# ===================================================================

def run_solven_analytics_pipeline(dataset_path):
    """Main entry point for analytics pipeline. Called by analytics_views.py."""
    try:
        _set_phase(0, "Starting", "Loading data...")

        # Load file
        if dataset_path.endswith('.csv'):
            try:
                df = pd.read_csv(dataset_path, encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(dataset_path, encoding="latin1")
        elif dataset_path.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(dataset_path)
        else:
            _set_error("Unsupported file format")
            return {"error": "Unsupported file format. Upload CSV or Excel."}

        if df.empty:
            _set_error("Empty file")
            return {"error": "The uploaded file contains no data."}

        df.columns = df.columns.str.strip()
        print(f"[Data] {len(df)} rows x {len(df.columns)} columns")

        numeric_stats = {}
        for col in df.select_dtypes(include=['number']).columns:
            try:
                numeric_stats[col] = {
                    "sum": float(df[col].sum()) if pd.notnull(df[col].sum()) else 0,
                    "mean": round(float(df[col].mean()), 2) if pd.notnull(df[col].mean()) else 0,
                    "min": float(df[col].min()) if pd.notnull(df[col].min()) else 0,
                    "max": float(df[col].max()) if pd.notnull(df[col].max()) else 0,
                    "count": int(df[col].count()),
                }
            except Exception:
                pass

        df_columns = list(df.columns)

        # PHASE 1
        _set_phase(1, "Data Profiling", "LLM Call 1/4")
        profile_data = _phase_1(df)
        if not profile_data or "dataset_profile" not in profile_data:
            print("[Phase 1] Using fallback profile")
            profile_data = {
                "dataset_profile": {
                    "total_rows": len(df),
                    "total_columns": len(df.columns),
                    "domain": "General",
                    "data_quality_score": "N/A",
                    "columns": [
                        {
                            "column_name": c,
                            "classification": (
                                "metric" if pd.api.types.is_numeric_dtype(df[c])
                                else "dimension"
                            ),
                            "null_percentage": round(
                                float(df[c].isnull().sum() / len(df) * 100), 2
                            ),
                        }
                        for c in df.columns
                    ],
                    "column_classifications": {
                        "metrics": list(df.select_dtypes(include=['number']).columns),
                        "dimensions": list(
                            df.select_dtypes(include=['object', 'category']).columns
                        ),
                        "temporal": [],
                        "identifiers": [],
                    },
                },
                "_numeric_stats": numeric_stats,
                "_categorical_stats": {},
                "_all_columns": df_columns,
                "_temporal_detected": [],
            }
        print("[Phase 1] Done")

        # PHASE 2+3
        _set_phase(2, "KPI Generation", "LLM Call 2/4")
        selected_kpis = _phase_2_3_combined(profile_data, numeric_stats)
        if not selected_kpis or not selected_kpis.get("selected_kpis"):
            _set_error("Could not generate KPIs")
            return {"error": "Could not generate KPIs from this dataset."}
        _set_phase(3, "KPI Prioritization", "Selected top 5")
        print(f"[Phase 2-3] Selected {len(selected_kpis['selected_kpis'])} KPIs")

        # PHASE 4
        _set_phase(4, "Formula Engineering", "LLM Call 3/4")
        kpi_formulas = _phase_4(selected_kpis, numeric_stats, df_columns)
        if not kpi_formulas or not kpi_formulas.get("kpis"):
            _set_error("Could not engineer formulas")
            return {"error": "Could not engineer KPI formulas."}
        print("[Phase 4] Done")

        # PHASE 5
        _set_phase(5, "KPI Computation", "Computing with Pandas")
        computed_kpis = _phase_5(kpi_formulas, df, numeric_stats)
        for kpi in computed_kpis.get("kpis", []):
            print(f"  -> {kpi['kpi_name']}: {kpi['kpi_value']}")
        print("[Phase 5] Done")

        # PHASE 6+7
        _set_phase(6, "Chart Ideation", "LLM Call 4/4")
        selected_charts = _phase_6_7_combined(profile_data, computed_kpis)
        if not selected_charts or not selected_charts.get("charts"):
            _set_error("Could not generate charts")
            return {"error": "Could not generate charts."}
        _set_phase(7, "Chart Selection", "Selected top 6")
        print(f"[Phase 6-7] Selected {len(selected_charts['charts'])} charts")

        # PHASE 8
        _set_phase(8, "Chart Data Generation", "Aggregating with Pandas")
        charts_with_data = _phase_8(df, selected_charts)
        for chart in charts_with_data.get("charts", []):
            print(f"  -> {chart.get('title', '?')}: {len(chart.get('data', []))} points")
        print("[Phase 8] Done")

        # PHASE 9
        _set_phase(9, "Final Consolidation", "Assembling output")
        final = _phase_9(profile_data, computed_kpis, charts_with_data, df)
        _set_complete()

        print("\n[Solven Analytics v2.0] Pipeline Complete!")
        return final

    except Exception as e:
        print(f"\n[ERROR] {e}")
        traceback.print_exc()
        _set_error(str(e))
        return {"error": f"Pipeline failed: {str(e)}"}


# ===================================================================
# ===================================================================
#
#   RAG QUERY SYSTEM — Hybrid Search + SQL + Knowledge Retrieval
#
# ===================================================================
# ===================================================================


def similarity_search(query, top_k=3):
    """
    Hybrid Search: Combines Vector Search (Semantic) + Keyword Search (Exact Match).
    Requires pgvector extension and document_chunks table.
    """
    query_embedding = generate_embedding(query)

    # 1. Vector Search (Semantic)
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT content, metadata, (embedding <=> %s::vector) as distance
            FROM document_chunks
            ORDER BY distance
            LIMIT %s
        """, [query_embedding, top_k])
        vector_results = cursor.fetchall()

    # 2. Keyword Search (Full-Text Search)
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT content, metadata, 0.0 as distance
            FROM document_chunks
            WHERE to_tsvector('english', content) @@ plainto_tsquery('english', %s)
            LIMIT %s
        """, [query, top_k])
        keyword_results = cursor.fetchall()

    # 3. Combine & Deduplicate
    combined_results = {}

    for row in vector_results:
        combined_results[row[0]] = {
            "content": row[0],
            "metadata": row[1],
            "distance": row[2],
        }

    for row in keyword_results:
        if row[0] not in combined_results:
            combined_results[row[0]] = {
                "content": row[0],
                "metadata": row[1],
                "distance": 0.0,
            }

    final_results = list(combined_results.values())
    final_results.sort(key=lambda x: x['distance'])

    return final_results[:top_k]


def rag_query(question, chat_history=None):
    """
    Main RAG query handler.
    Routes to: Database (SQL) | Knowledge (RAG) | Conversational | Irrelevant.
    """

    # -------------------------
    # 0. Contextualize Question (Memory)
    # -------------------------
    search_query = question

    if chat_history and len(chat_history) > 0:
        history_text = "\n".join([
            f"{msg['role']}: {msg['content']}"
            for msg in chat_history[-4:]
        ])

        rewrite_prompt = f"""
Given the following conversation history and a follow-up question, rephrase the follow-up question to be a standalone question that can be understood without the history.

Chat History:
{history_text}

Follow-up Question: {question}

Standalone Question:
"""
        rewritten = generate_response(rewrite_prompt).strip()

        if "Standalone Question:" in rewritten:
            rewritten = rewritten.split("Standalone Question:")[-1].strip()

        print(f"DEBUG: Original: '{question}' -> Rewritten: '{rewritten}'")
        search_query = rewritten

    # -------------------------
    # 1. Classify question
    # -------------------------
    classification_prompt = f"""
Classify the user's question into ONE of the following categories:

database: For questions about Titanic passengers, such as counts, details, ages, survival, fares, or lists (e.g., "show me details of women", "how many men").
knowledge: For questions about company policy, employment, leave, travel, office environment, or any specific terms defined in the documents.
conversational: ONLY for greetings (hello, hi) or simple pleasantries.
irrelevant: For questions completely unrelated to the Titanic dataset or company policy.
Return ONLY one word.

Question:
{search_query}
"""

    question_type = generate_response(classification_prompt).strip().lower()
    print(f"DEBUG: Question '{search_query}' classified as: {question_type}")

    # -------------------------
    # 2. Database -> Generate SQL
    # -------------------------
    if "database" in question_type:

        sql_prompt = f"""
You are a PostgreSQL expert tasked with converting natural language questions into PostgreSQL queries for the 'titanic' table.

Table Schema:

table_name: titanic
columns:
survived: INTEGER (0 = No, 1 = Yes)
pclass: INTEGER (Passenger Class: 1, 2, 3)
sex: TEXT ('male', 'female')
age: FLOAT (can be NULL)
sibsp: INTEGER (Number of Siblings/Spouses Aboard)
parch: INTEGER (Number of Parents/Children Aboard)
fare: FLOAT
embarked: TEXT (Port of Embarkation: 'C' = Cherbourg, 'Q' = Queenstown, 'S' = Southampton)

STRICT RULES:
- Return ONLY raw SQL. No markdown, no explanations, just the query.
- Use exact column names and values (e.g., sex = 'female', not 'woman').
- When filtering by age, always exclude NULLs (e.g., WHERE age IS NOT NULL AND ...).
- For general counts of passengers, use COUNT(*).
- For questions about survival, use survived = 1. For non-survival, use survived = 0.
- Do NOT add survived = 1 unless the user explicitly asks about survival.
- Map 'women'/'woman' to sex = 'female' and 'men'/'man' to sex = 'male'.

Examples:

User Question: "How many passengers survived?"
SQL Query: SELECT COUNT(*) FROM titanic WHERE survived = 1;

User Question: "What is the total count of passengers?"
SQL Query: SELECT COUNT(*) FROM titanic;

User Question: "how many passengers were in pclass 1"
SQL Query: SELECT COUNT(*) FROM titanic WHERE pclass = 1;

User Question: "count of male and female passengers"
SQL Query: SELECT sex, COUNT(*) FROM titanic GROUP BY sex;

User Question: "give me details of women age group between 20 to 50"
SQL Query: SELECT * FROM titanic WHERE sex = 'female' AND age BETWEEN 20 AND 50;

User Question:
{search_query}

SQL Query:
"""

        sql_query = generate_response(sql_prompt).strip()

        # Remove markdown formatting if LLM adds it
        match = re.search(
            r"```(?:sql)?\s*(.*?)```", sql_query, re.DOTALL | re.IGNORECASE
        )
        if match:
            sql_query = match.group(1).strip()
        else:
            sql_query = sql_query.replace("```sql", "").replace("```", "").strip()

        # Safety check
        forbidden_keywords = ["drop", "delete", "update", "insert", "alter", "truncate"]
        if any(keyword in sql_query.lower() for keyword in forbidden_keywords):
            return "Unsafe query detected."

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_query)
                result = cursor.fetchall()

            if not result:
                return "No records found."

            if len(result) == 1 and len(result[0]) == 1:
                return f"The answer is {result[0][0]}."

            return f"Query Result: {result}"

        except Exception as e:
            return f"Error executing generated SQL: {str(e)}"

    # -------------------------
    # 3. Knowledge -> Use RAG
    # -------------------------
    if "knowledge" in question_type:

        docs = similarity_search(search_query, top_k=5)

        if not docs:
            return "No relevant information found."

        context = "\n\n".join([doc["content"] for doc in docs])

        prompt = f"""You are a helpful assistant. Your task is to answer the user's question based *only* on the provided context.
Do not mention the context in your answer. Just provide the answer directly.
If the information is not in the context, state that the answer is not available in the provided data.

Context:
{context}

User's Question:
{search_query}

Answer:
"""

        return generate_response(prompt)

    # -------------------------
    # 3b. Conversational
    # -------------------------
    if "conversational" in question_type:
        return generate_response(
            f"Respond politely to this conversational input: {search_query}"
        )

    # -------------------------
    # 4. Irrelevant
    # -------------------------
    return "Please ask a question related to the dataset."

# """
# Solven Analytics Engine v2.0 — Core 9-Phase Analytical Pipeline
# ================================================================
# Orchestrates LLM intelligence (Ollama) + Pandas computation to
# transform raw datasets into executive-grade KPIs, charts, and insights.

# Pipeline:
#   Phase 1: Data Profiling & Schema Understanding
#   Phase 2: Exhaustive KPI Generation (10-20+)
#   Phase 3: KPI Prioritization & Selection (Top 5)
#   Phase 4: Formula Engineering & Computation Logic
#   Phase 5: Structured KPI Output (Dashboard-Ready)
#   Phase 6: Chart Ideation & Visualization Mapping (10+)
#   Phase 7: Chart Prioritization & Selection (Top 6)
#   Phase 8: Structured Chart Output (Render-Ready)
#   Phase 9: Final Consolidated Output Package
# """

# import json
# import pandas as pd
# import numpy as np
# import datetime
# import traceback
# from api.ollama_service import generate_response


# # ═══════════════════════════════════════════════════════════════
# # UTILITY HELPERS
# # ═══════════════════════════════════════════════════════════════

# def _safe_json_loads(json_str):
#     """
#     Robust JSON parser that handles common LLM output quirks:
#     - Markdown code fences (```json ... ```)
#     - Leading/trailing text outside JSON
#     - Nested brace matching
#     """
#     if not json_str or not isinstance(json_str, str):
#         return {}

#     try:
#         cleaned = json_str.strip()

#         # ── Extract from markdown code fences ──
#         if "```json" in cleaned:
#             cleaned = cleaned.split("```json", 1)[1]
#             cleaned = cleaned.split("```", 1)[0]
#         elif "```" in cleaned:
#             parts = cleaned.split("```")
#             if len(parts) >= 3:
#                 cleaned = parts[1]
#                 # Strip language hint on first line (e.g., "python\n")
#                 first_newline = cleaned.find('\n')
#                 if first_newline != -1 and first_newline < 20:
#                     maybe_lang = cleaned[:first_newline].strip()
#                     if maybe_lang.isalpha():
#                         cleaned = cleaned[first_newline:]

#         cleaned = cleaned.strip()

#         # ── Try direct parse ──
#         return json.loads(cleaned)

#     except json.JSONDecodeError:
#         # ── Fallback: locate outermost JSON object or array ──
#         try:
#             start_obj = cleaned.find('{')
#             start_arr = cleaned.find('[')

#             if start_obj == -1 and start_arr == -1:
#                 return {}

#             # Determine whether outermost is { or [
#             if start_arr != -1 and (start_obj == -1 or start_arr < start_obj):
#                 start, open_c, close_c = start_arr, '[', ']'
#             else:
#                 start, open_c, close_c = start_obj, '{', '}'

#             depth = 0
#             for i in range(start, len(cleaned)):
#                 if cleaned[i] == open_c:
#                     depth += 1
#                 elif cleaned[i] == close_c:
#                     depth -= 1
#                 if depth == 0:
#                     return json.loads(cleaned[start:i + 1])
#         except Exception:
#             pass

#         print(f"[JSON Parser] Failed to parse. Preview: {json_str[:300]}")
#         return {}

#     except Exception as e:
#         print(f"[JSON Parser] Unexpected error: {e}")
#         return {}


# def _llm_call_with_retry(prompt, max_retries=2):
#     """Call the LLM with automatic retry on empty/invalid responses."""
#     for attempt in range(max_retries + 1):
#         try:
#             raw = generate_response(prompt)
#             result = _safe_json_loads(raw)
#             if result:
#                 return result
#             if attempt < max_retries:
#                 print(f"[LLM Retry] Empty result on attempt {attempt + 1}, retrying…")
#                 prompt += (
#                     "\n\nCRITICAL REMINDER: You MUST respond with ONLY valid JSON. "
#                     "No markdown, no explanation, no text outside the JSON object."
#                 )
#         except Exception as e:
#             print(f"[LLM Retry] Error on attempt {attempt + 1}: {e}")
#     return {}


# def _make_json_serializable(obj):
#     """Recursively convert numpy/pandas types to native Python types."""
#     if isinstance(obj, dict):
#         return {k: _make_json_serializable(v) for k, v in obj.items()}
#     elif isinstance(obj, list):
#         return [_make_json_serializable(v) for v in obj]
#     elif isinstance(obj, (np.int64, np.int32, np.int16, np.int8)):
#         return int(obj)
#     elif isinstance(obj, (np.float64, np.float32, np.float16)):
#         return float(obj) if not np.isnan(obj) else 0
#     elif isinstance(obj, np.bool_):
#         return bool(obj)
#     elif isinstance(obj, (pd.Timestamp, datetime.datetime)):
#         return obj.isoformat()
#     elif pd.isna(obj):
#         return None
#     return obj


# # ═══════════════════════════════════════════════════════════════
# # DATA HELPERS
# # ═══════════════════════════════════════════════════════════════

# def _build_comprehensive_profile(df):
#     """
#     Build a rich statistical profile of the entire DataFrame.
#     This is the raw material that Phase 1's LLM prompt will use.
#     """
#     profile = {
#         "total_rows": len(df),
#         "total_columns": len(df.columns),
#         "columns": [],
#         "numeric_stats": {},
#         "categorical_stats": {},
#         "temporal_columns_detected": [],
#         "sample_data": _make_json_serializable(
#             df.head(5).fillna("NULL").to_dict(orient='records')
#         ),
#     }

#     for col in df.columns:
#         col_info = {
#             "column_name": col,
#             "pandas_dtype": str(df[col].dtype),
#             "null_count": int(df[col].isnull().sum()),
#             "null_percentage": round(
#                 float(df[col].isnull().sum() / len(df) * 100), 2
#             ),
#             "unique_values": int(df[col].nunique()),
#             "total_non_null": int(df[col].count()),
#             "is_numeric": False,
#             "is_categorical": False,
#             "is_temporal": False,
#         }

#         # Sample values
#         non_null = df[col].dropna()
#         col_info["sample_values"] = (
#             [str(v) for v in non_null.head(5).tolist()] if len(non_null) > 0 else []
#         )

#         # ── Numeric columns ──
#         if pd.api.types.is_numeric_dtype(df[col]):
#             col_info["is_numeric"] = True
#             try:
#                 stats = {
#                     "sum": float(df[col].sum()) if pd.notnull(df[col].sum()) else 0,
#                     "mean": round(float(df[col].mean()), 4) if pd.notnull(df[col].mean()) else 0,
#                     "median": float(df[col].median()) if pd.notnull(df[col].median()) else 0,
#                     "min": float(df[col].min()) if pd.notnull(df[col].min()) else 0,
#                     "max": float(df[col].max()) if pd.notnull(df[col].max()) else 0,
#                     "std": round(float(df[col].std()), 4) if pd.notnull(df[col].std()) else 0,
#                     "count": int(df[col].count()),
#                 }
#                 col_info["stats"] = stats
#                 profile["numeric_stats"][col] = stats
#             except Exception:
#                 col_info["is_numeric"] = False

#         # ── Categorical columns ──
#         if df[col].dtype == 'object' or df[col].dtype.name == 'category':
#             col_info["is_categorical"] = True
#             try:
#                 vc = df[col].value_counts().head(10)
#                 col_info["top_values"] = {str(k): int(v) for k, v in vc.items()}
#                 profile["categorical_stats"][col] = col_info["top_values"]
#             except Exception:
#                 pass

#         # ── Temporal detection ──
#         if pd.api.types.is_datetime64_any_dtype(df[col]):
#             col_info["is_temporal"] = True
#             profile["temporal_columns_detected"].append(col)
#         elif df[col].dtype == 'object':
#             try:
#                 sample = df[col].dropna().head(30)
#                 parsed = pd.to_datetime(sample, infer_datetime_format=True, errors='coerce')
#                 if parsed.notna().sum() >= len(sample) * 0.7:
#                     col_info["is_temporal"] = True
#                     col_info["temporal_inferred"] = True
#                     profile["temporal_columns_detected"].append(col)
#             except Exception:
#                 pass

#         profile["columns"].append(col_info)

#     return _make_json_serializable(profile)


# def _compute_kpi_value(df, kpi_spec):
#     """
#     Compute a KPI value using Pandas, driven by the LLM-defined formula.
#     Uses pattern-matching on the formula string + columns_used list.
#     """
#     try:
#         formula = kpi_spec.get("formula", "").lower()
#         columns_used = kpi_spec.get("columns_used", [])

#         # Validate that referenced columns actually exist
#         valid_cols = [c for c in columns_used if c in df.columns]
#         if not valid_cols:
#             return None

#         # ── MULTIPLICATION + SUM  (e.g. SUM(Qty * Price)) ──
#         if ("*" in formula or "×" in formula) and (
#             "sum" in formula
#         ):
#             if len(valid_cols) >= 2:
#                 return float((df[valid_cols[0]] * df[valid_cols[1]]).sum())

#         # ── RATIO / PERCENTAGE / MARGIN ──
#         if any(w in formula for w in ["ratio", "%", "margin", "percentage", "/"]):
#             if len(valid_cols) >= 2:
#                 denom = df[valid_cols[1]].sum()
#                 if denom and denom != 0:
#                     return round(float(df[valid_cols[0]].sum() / denom * 100), 2)
#             if len(valid_cols) == 1 and "count" in formula:
#                 total = len(df)
#                 return round(float(df[valid_cols[0]].sum() / total * 100), 2) if total else 0

#         # ── SUM ──
#         if "sum" in formula:
#             if len(valid_cols) >= 1 and pd.api.types.is_numeric_dtype(df[valid_cols[0]]):
#                 return float(df[valid_cols[0]].sum())

#         # ── AVERAGE / MEAN ──
#         if any(w in formula for w in ["avg", "average", "mean"]):
#             if len(valid_cols) >= 2 and ("*" in formula or "×" in formula):
#                 return float((df[valid_cols[0]] * df[valid_cols[1]]).mean())
#             if len(valid_cols) >= 1 and pd.api.types.is_numeric_dtype(df[valid_cols[0]]):
#                 return round(float(df[valid_cols[0]].mean()), 2)

#         # ── COUNT DISTINCT / UNIQUE ──
#         if "distinct" in formula or "unique" in formula:
#             return int(df[valid_cols[0]].nunique())

#         # ── COUNT ──
#         if "count" in formula:
#             return int(df[valid_cols[0]].count())

#         # ── MAX ──
#         if "max" in formula:
#             if pd.api.types.is_numeric_dtype(df[valid_cols[0]]):
#                 return float(df[valid_cols[0]].max())

#         # ── MIN ──
#         if "min" in formula:
#             if pd.api.types.is_numeric_dtype(df[valid_cols[0]]):
#                 return float(df[valid_cols[0]].min())

#         # ── DIFFERENCE (e.g. Revenue - Cost) ──
#         if "-" in formula and len(valid_cols) >= 2:
#             if pd.api.types.is_numeric_dtype(df[valid_cols[0]]) and pd.api.types.is_numeric_dtype(df[valid_cols[1]]):
#                 return float(df[valid_cols[0]].sum() - df[valid_cols[1]].sum())

#         # ── Fallback: SUM of first numeric column ──
#         if pd.api.types.is_numeric_dtype(df[valid_cols[0]]):
#             return float(df[valid_cols[0]].sum())

#         return None

#     except Exception as e:
#         print(f"[KPI Compute] Error for '{kpi_spec.get('kpi_name', '?')}': {e}")
#         return None


# def _format_kpi_value(value, kpi_name=""):
#     """Format a numeric value for dashboard display."""
#     if value is None:
#         return "N/A"

#     name_lower = kpi_name.lower()

#     # Percentage
#     if any(w in name_lower for w in ['rate', 'margin', 'percentage', 'ratio', '%', 'share']):
#         return f"{value:.2f}%"

#     # Currency
#     if any(w in name_lower for w in [
#         'revenue', 'profit', 'cost', 'price', 'sales',
#         'income', 'expense', 'value', 'spend', 'amount'
#     ]):
#         if abs(value) >= 1_000_000_000:
#             return f"${value / 1_000_000_000:,.2f}B"
#         if abs(value) >= 1_000_000:
#             return f"${value / 1_000_000:,.2f}M"
#         if abs(value) >= 1_000:
#             return f"${value:,.2f}"
#         return f"${value:.2f}"

#     # Integer counts
#     if any(w in name_lower for w in ['count', 'total', 'number', 'orders', 'customers', 'transactions']):
#         return f"{int(value):,}"

#     # Default numeric
#     if isinstance(value, float):
#         if value == int(value) and abs(value) < 1e15:
#             return f"{int(value):,}"
#         return f"{value:,.2f}"

#     return str(value)


# def _generate_chart_data(df, chart_spec):
#     """
#     Execute a Pandas aggregation to produce actual data points for a chart.
#     Returns list of dicts: [{"name": ..., "value": ...}, ...]
#     For scatter charts: [{"x": ..., "y": ...}, ...]
#     """
#     try:
#         x_col = chart_spec.get("x_axis", {}).get("column", "")
#         y_col = chart_spec.get("y_axis", {}).get("column", "")
#         aggregation = chart_spec.get("y_axis", {}).get("aggregation", "SUM").upper()
#         chart_type = chart_spec.get("chart_type", "").lower()
#         sort_order = chart_spec.get("sort_order", "")

#         # ── Scatter plot ──
#         if chart_type == "scatter":
#             if x_col in df.columns and y_col in df.columns:
#                 scatter = df[[x_col, y_col]].dropna()
#                 if pd.api.types.is_numeric_dtype(scatter[x_col]) and pd.api.types.is_numeric_dtype(scatter[y_col]):
#                     sample = scatter.head(200)
#                     return _make_json_serializable(
#                         [{"x": row[x_col], "y": row[y_col]} for _, row in sample.iterrows()]
#                     )
#             return []

#         # ── Histogram ──
#         if chart_type == "histogram":
#             target = x_col if x_col in df.columns else y_col
#             if target in df.columns and pd.api.types.is_numeric_dtype(df[target]):
#                 counts, edges = np.histogram(df[target].dropna(), bins=10)
#                 return [
#                     {"name": f"{edges[i]:.1f}–{edges[i+1]:.1f}", "value": int(counts[i])}
#                     for i in range(len(counts))
#                 ]
#             return []

#         # ── Standard grouped aggregation ──
#         if not x_col or x_col not in df.columns:
#             return []

#         # Determine if Y needs to be computed
#         if not y_col or y_col not in df.columns:
#             if aggregation == "COUNT":
#                 grouped = df.groupby(x_col).size().reset_index(name='value')
#                 grouped = grouped.rename(columns={x_col: 'name'})
#             else:
#                 # Fallback to count
#                 grouped = df[x_col].value_counts().reset_index()
#                 grouped.columns = ['name', 'value']
#         else:
#             agg_map = {
#                 "SUM": "sum",
#                 "AVG": "mean",
#                 "MEAN": "mean",
#                 "AVERAGE": "mean",
#                 "COUNT": "count",
#                 "MAX": "max",
#                 "MIN": "min",
#                 "MEDIAN": "median",
#             }
#             agg_func = agg_map.get(aggregation, "sum")
#             grouped = df.groupby(x_col)[y_col].agg(agg_func).reset_index()
#             grouped.columns = ['name', 'value']

#         # Sort
#         if sort_order == "descending":
#             grouped = grouped.sort_values('value', ascending=False)
#         elif sort_order == "ascending":
#             grouped = grouped.sort_values('value', ascending=True)

#         grouped['name'] = grouped['name'].astype(str)

#         if pd.api.types.is_numeric_dtype(grouped['value']):
#             grouped['value'] = grouped['value'].round(2)

#         result = grouped.head(15).to_dict(orient='records')
#         return _make_json_serializable(result)

#     except Exception as e:
#         print(f"[Chart Data] Error for '{chart_spec.get('title', '?')}': {e}")
#         traceback.print_exc()
#         return []


# # ═══════════════════════════════════════════════════════════════
# #  PHASE 1 — DATA PROFILING & SCHEMA UNDERSTANDING
# # ═══════════════════════════════════════════════════════════════

# def _phase_1_data_profiling(df):
#     """
#     Phase 1: Comprehensive structural and semantic analysis.
#     - Detects schema, data types, statistics
#     - Classifies every column as METRIC / DIMENSION / TEMPORAL / IDENTIFIER
#     - Audits data quality
#     """
#     profile = _build_comprehensive_profile(df)

#     prompt = f"""You are the Solven Analytics Data Profiling Engine — Phase 1.

# Your task is to perform a comprehensive structural and semantic analysis of the provided dataset.

# ═══ DATASET STATISTICS ═══
# - Total Rows: {profile['total_rows']}
# - Total Columns: {profile['total_columns']}

# ═══ COLUMN DETAILS ═══
# {json.dumps(profile['columns'], indent=2)}

# ═══ SAMPLE DATA (first 5 rows) ═══
# {json.dumps(profile['sample_data'], indent=2)}

# ═══ YOUR TASKS ═══
# 1. Classify EVERY column into EXACTLY ONE role:
#    - "metric"     → Quantitative, aggregatable numeric fields (Revenue, Price, Quantity)
#    - "dimension"  → Categorical fields for grouping/filtering (Product, Region, Category)
#    - "temporal"   → Date/time fields for trend analysis (Order Date, Month, Year)
#    - "identifier" → Unique keys NOT used for aggregation (Order ID, Customer ID)

# 2. Infer the business meaning of each column from its name, values, and context.

# 3. Detect the business domain (e-commerce, finance, healthcare, HR, etc.).

# 4. Provide a data quality score (0-100%).

# ═══ RESPONSE FORMAT ═══
# Respond with ONLY this JSON — no other text:
# {{
#   "dataset_profile": {{
#     "total_rows": {profile['total_rows']},
#     "total_columns": {profile['total_columns']},
#     "domain": "detected business domain",
#     "data_quality_score": "85%",
#     "columns": [
#       {{
#         "column_name": "exact column name from dataset",
#         "data_type": "numeric | categorical | datetime | boolean | text",
#         "classification": "metric | dimension | temporal | identifier",
#         "business_meaning": "concise business description",
#         "null_percentage": 0.0,
#         "unique_values": 0,
#         "sample_values": ["val1", "val2", "val3"]
#       }}
#     ],
#     "column_classifications": {{
#       "metrics": ["list of metric column names"],
#       "dimensions": ["list of dimension column names"],
#       "temporal": ["list of temporal column names"],
#       "identifiers": ["list of identifier column names"]
#     }}
#   }}
# }}"""

#     result = _llm_call_with_retry(prompt)

#     # Attach raw stats for downstream phases
#     if result:
#         result["_numeric_stats"] = profile.get("numeric_stats", {})
#         result["_categorical_stats"] = profile.get("categorical_stats", {})
#         result["_all_columns"] = [c["column_name"] for c in profile["columns"]]
#         result["_temporal_detected"] = profile.get("temporal_columns_detected", [])

#     return result


# # ═══════════════════════════════════════════════════════════════
# #  PHASE 2 — EXHAUSTIVE KPI GENERATION (10-20+)
# # ═══════════════════════════════════════════════════════════════

# def _phase_2_kpi_generation(profile_data, numeric_stats, df):
#     """
#     Phase 2: Generate 10-20 meaningful, data-supported KPIs
#     across Financial, Operational, Growth, Customer, and Performance categories.
#     """
#     dp = profile_data.get("dataset_profile", {})
#     classifications = dp.get("column_classifications", {})

#     # Build rich context for the LLM
#     col_descriptions = ""
#     for col in dp.get("columns", []):
#         col_descriptions += (
#             f"  • {col['column_name']} "
#             f"[{col.get('classification', 'unknown').upper()}] "
#             f"— {col.get('business_meaning', 'N/A')}\n"
#         )

#     prompt = f"""You are the Solven Analytics KPI Generation Engine — Phase 2.

# ═══ DATASET CONTEXT ═══
# Domain: {dp.get('domain', 'General Business')}
# Total Rows: {dp.get('total_rows', 0)}
# Total Columns: {dp.get('total_columns', 0)}

# ═══ COLUMN MAP ═══
# {col_descriptions}

# ═══ NUMERIC STATISTICS ═══
# {json.dumps(numeric_stats, indent=2)}

# ═══ CATEGORICAL BREAKDOWN ═══
# {json.dumps(profile_data.get('_categorical_stats', {}), indent=2)}

# ═══ YOUR TASK ═══
# Generate 15-20 meaningful KPIs across these categories:

# 💰 FINANCIAL KPIs — Revenue, Profit, Margins, Costs, Average Order Value
# 📦 OPERATIONAL KPIs — Total Orders, Quantities, Basket Size, Fulfillment
# 📈 GROWTH & TREND KPIs — MoM Growth, YoY Growth, Sales Velocity
# 👥 CUSTOMER KPIs — Lifetime Value, Segments, Retention, Acquisition
# 🏆 PERFORMANCE KPIs — Top Performers, Rankings, Contribution %

# ═══ RULES ═══
# 1. ONLY reference columns that actually exist in the dataset
# 2. Each KPI must be COMPUTABLE from the available data
# 3. Include a mix of simple (1-column) and complex (multi-column) KPIs
# 4. Provide the exact mathematical formula using the exact column names
# 5. Do NOT fabricate columns that do not exist

# ═══ RESPONSE FORMAT ═══
# Respond with ONLY this JSON:
# {{
#   "generated_kpis": [
#     {{
#       "kpi_name": "Clear, business-standard name",
#       "category": "FINANCIAL | OPERATIONAL | GROWTH | CUSTOMER | PERFORMANCE",
#       "business_meaning": "What this KPI measures in business terms",
#       "formula": "Mathematical formula using EXACT column names, e.g. SUM(Quantity × Unit_Price)",
#       "columns_used": ["ExactColumnName1", "ExactColumnName2"],
#       "strategic_importance": "Why this KPI matters for decision-making",
#       "complexity": "simple | moderate | complex"
#     }}
#   ]
# }}"""

#     return _llm_call_with_retry(prompt)


# # ═══════════════════════════════════════════════════════════════
# #  PHASE 3 — KPI PRIORITIZATION & SELECTION (TOP 5)
# # ═══════════════════════════════════════════════════════════════

# def _phase_3_kpi_prioritization(generated_kpis, profile_data):
#     """
#     Phase 3: Select the 5 most impactful KPIs using a weighted scoring matrix.
#     """
#     prompt = f"""You are the Solven Analytics KPI Prioritization Engine — Phase 3.

# ═══ ALL GENERATED KPIs ═══
# {json.dumps(generated_kpis.get('generated_kpis', []), indent=2)}

# ═══ WEIGHTED SCORING CRITERIA ═══
# Apply these weights to score every KPI, then select the TOP 5:

#   1. Decision-Making Impact           (25%)
#   2. Actionability & Clarity          (20%)
#   3. Business Performance Reflection  (20%)
#   4. Strategic & Growth Relevance     (15%)
#   5. Data Relationship Depth          (10%)
#   6. Executive-Level Significance     (10%)

# ═══ MANDATORY SELECTION RULES ═══
# • Select EXACTLY 5 KPIs
# • Ensure DIVERSITY — no two KPIs should measure the same dimension
# • Prefer KPIs that combine multiple columns over single-column aggregations
# • At least ONE KPI must represent trends/growth
# • At least ONE KPI must represent performance ranking
# • Include the priority_score (0-100) showing how each KPI was scored

# ═══ RESPONSE FORMAT ═══
# Respond with ONLY this JSON:
# {{
#   "selected_kpis": [
#     {{
#       "kpi_name": "Name",
#       "category": "FINANCIAL | OPERATIONAL | GROWTH | CUSTOMER | PERFORMANCE",
#       "business_meaning": "What it measures",
#       "formula": "Exact formula with column names",
#       "columns_used": ["Col1", "Col2"],
#       "strategic_importance": "Why it was selected",
#       "priority_score": 92,
#       "selection_reason": "Detailed reason for prioritization"
#     }}
#   ]
# }}"""

#     return _llm_call_with_retry(prompt)


# # ═══════════════════════════════════════════════════════════════
# #  PHASE 4 — FORMULA ENGINEERING & COMPUTATION LOGIC
# # ═══════════════════════════════════════════════════════════════

# def _phase_4_formula_engineering(selected_kpis, numeric_stats, df_columns):
#     """
#     Phase 4: For each of the Top 5 KPIs, produce complete computation specs
#     including formula, Python, SQL, and plain-language explanation.
#     """
#     prompt = f"""You are the Solven Analytics Formula Engineering Engine — Phase 4.

# ═══ SELECTED TOP 5 KPIs ═══
# {json.dumps(selected_kpis.get('selected_kpis', []), indent=2)}

# ═══ AVAILABLE COLUMNS IN DATASET ═══
# {json.dumps(df_columns)}

# ═══ PRE-COMPUTED NUMERIC STATISTICS ═══
# {json.dumps(numeric_stats, indent=2)}

# ═══ YOUR TASK ═══
# For EACH of the 5 KPIs, provide:
# 1. The precise mathematical formula
# 2. A plain-language explanation
# 3. Python (Pandas) equivalent code
# 4. SQL equivalent query
# 5. Row-level vs table-level aggregation logic
# 6. Trend direction based on the data pattern
# 7. Strategic priority (HIGH / MEDIUM / LOW)
# 8. A business insight about what the computed value means
# 9. An actionable recommendation

# ═══ IMPORTANT ═══
# • Use ONLY columns from AVAILABLE COLUMNS — do NOT invent column names
# • Python code must use standard Pandas operations (df['col'].sum(), etc.)
# • If a KPI requires columns that don't exist, adjust the formula to use available columns

# ═══ RESPONSE FORMAT ═══
# Respond with ONLY this JSON:
# {{
#   "kpis": [
#     {{
#       "kpi_id": "KPI-001",
#       "kpi_name": "Total Revenue",
#       "formula": "SUM(Quantity × Unit_Price)",
#       "columns_used": ["Quantity", "Unit_Price"],
#       "computation_method": {{
#         "python": "(df['Quantity'] * df['Unit_Price']).sum()",
#         "sql": "SELECT SUM(Quantity * Unit_Price) AS Total_Revenue FROM dataset"
#       }},
#       "aggregation_logic": {{
#         "row_level": "Quantity × Unit_Price",
#         "table_level": "SUM of all row-level results"
#       }},
#       "plain_language": "Calculates total revenue by multiplying quantity by price per row, then summing all rows.",
#       "trend_direction": "up | down | stable",
#       "strategic_priority": "HIGH | MEDIUM | LOW",
#       "business_insight": "Specific insight about what the value reveals about the business.",
#       "actionable_recommendation": "Specific action to take based on this KPI."
#     }}
#   ]
# }}"""

#     return _llm_call_with_retry(prompt)


# # ═══════════════════════════════════════════════════════════════
# #  PHASE 5 — KPI COMPUTATION (PANDAS-DRIVEN)
# # ═══════════════════════════════════════════════════════════════

# def _phase_5_compute_kpis(kpi_specs, df, numeric_stats):
#     """
#     Phase 5: Compute actual KPI values using Pandas.
#     The LLM defined the formulas; Pandas executes them for accuracy.
#     """
#     computed_kpis = []
#     kpis_list = kpi_specs.get("kpis", [])

#     for idx, kpi in enumerate(kpis_list):
#         # ── Compute value via Pandas ──
#         computed_value = _compute_kpi_value(df, kpi)

#         # ── Fallback: use pre-calculated numeric stats ──
#         if computed_value is None:
#             columns = kpi.get("columns_used", [])
#             formula = kpi.get("formula", "").lower()

#             for col in columns:
#                 if col in numeric_stats:
#                     if "sum" in formula:
#                         computed_value = numeric_stats[col].get("sum")
#                     elif any(w in formula for w in ["avg", "mean", "average"]):
#                         computed_value = numeric_stats[col].get("mean")
#                     elif "max" in formula:
#                         computed_value = numeric_stats[col].get("max")
#                     elif "min" in formula:
#                         computed_value = numeric_stats[col].get("min")
#                     elif "count" in formula:
#                         computed_value = numeric_stats[col].get("count")
#                     if computed_value is not None:
#                         break

#         kpi_name = kpi.get("kpi_name", f"KPI {idx + 1}")

#         computed_kpi = {
#             "kpi_id": kpi.get("kpi_id", f"KPI-{idx + 1:03d}"),
#             "kpi_name": kpi_name,
#             "kpi_value": _format_kpi_value(computed_value, kpi_name),
#             "kpi_value_raw": computed_value if computed_value is not None else 0,
#             "trend_direction": kpi.get("trend_direction", "stable"),
#             "formula": kpi.get("formula", ""),
#             "columns_used": kpi.get("columns_used", []),
#             "computation_method": kpi.get("computation_method", {}),
#             "business_insight": kpi.get("business_insight", ""),
#             "actionable_recommendation": kpi.get("actionable_recommendation", ""),
#             "strategic_priority": kpi.get("strategic_priority", "MEDIUM"),
#         }
#         computed_kpis.append(computed_kpi)

#     return {"kpis": computed_kpis}


# # ═══════════════════════════════════════════════════════════════
# #  PHASE 6 — CHART IDEATION & VISUALIZATION MAPPING (10+)
# # ═══════════════════════════════════════════════════════════════

# def _phase_6_chart_ideation(profile_data, computed_kpis):
#     """
#     Phase 6: Generate 10+ visualization concepts that surface
#     meaningful patterns, trends, and comparisons.
#     """
#     dp = profile_data.get("dataset_profile", {})
#     classifications = dp.get("column_classifications", {})

#     prompt = f"""You are the Solven Analytics Chart Ideation Engine — Phase 6.

# ═══ DATASET CONTEXT ═══
# Domain: {dp.get('domain', 'Business')}
# Total Rows: {dp.get('total_rows', 0)}

# ═══ COLUMN CLASSIFICATIONS ═══
# METRIC columns (numeric, aggregatable):   {json.dumps(classifications.get('metrics', []))}
# DIMENSION columns (categorical, grouping): {json.dumps(classifications.get('dimensions', []))}
# TEMPORAL columns (date/time):              {json.dumps(classifications.get('temporal', []))}
# IDENTIFIER columns (unique keys):          {json.dumps(classifications.get('identifiers', []))}

# ═══ COMPUTED KPIs ═══
# {json.dumps([{{"name": k["kpi_name"], "value": k["kpi_value"], "columns": k["columns_used"]}} for k in computed_kpis.get("kpis", [])], indent=2)}

# ═══ SUPPORTED CHART TYPES ═══
# bar, line, pie, donut, area, scatter, histogram, stacked_bar, grouped_bar, heatmap, waterfall, treemap

# ═══ YOUR TASK ═══
# Generate 10-12 visualization concepts. Each chart must:
# 1. Use ONLY columns that exist in the dataset
# 2. Serve a distinct analytical purpose
# 3. Have x_axis mapped to a DIMENSION or TEMPORAL column
# 4. Have y_axis mapped to a METRIC column (except histogram/scatter)
# 5. Include the aggregation type (SUM, AVG, COUNT, MAX, MIN, DISTINCT)

# ═══ ENSURE VARIETY ═══
# Include: time-series (line/area), comparisons (bar), distributions (pie/histogram),
# relationships (scatter), compositions (stacked_bar/treemap)

# ═══ RESPONSE FORMAT ═══
# Respond with ONLY this JSON:
# {{
#   "chart_concepts": [
#     {{
#       "chart_type": "bar",
#       "title": "Descriptive Chart Title",
#       "x_axis": {{
#         "column": "ExactColumnName",
#         "label": "Human-readable label"
#       }},
#       "y_axis": {{
#         "column": "ExactColumnName",
#         "label": "Human-readable label",
#         "aggregation": "SUM"
#       }},
#       "group_by": null,
#       "sort_order": "descending | ascending | none",
#       "business_meaning": "What insight does this chart reveal?",
#       "decision_value": "How does this help decision-making?",
#       "insight_type": "comparison | trend | distribution | relationship | composition"
#     }}
#   ]
# }}"""

#     return _llm_call_with_retry(prompt)


# # ═══════════════════════════════════════════════════════════════
# #  PHASE 7 — CHART PRIORITIZATION & SELECTION (TOP 6)
# # ═══════════════════════════════════════════════════════════════

# def _phase_7_chart_selection(chart_concepts):
#     """
#     Phase 7: Select the 6 most impactful visualizations for the dashboard.
#     Enforces diversity rules.
#     """
#     prompt = f"""You are the Solven Analytics Chart Selection Engine — Phase 7.

# ═══ ALL CHART CONCEPTS ═══
# {json.dumps(chart_concepts.get('chart_concepts', []), indent=2)}

# ═══ SELECTION CRITERIA ═══
# Score each chart on:
# 1. Clarity of business insight
# 2. Decision-making enablement
# 3. Performance analysis depth
# 4. Trend / pattern visibility
# 5. Cross-category comparison value
# 6. Strategic and executive relevance

# ═══ MANDATORY DIVERSITY RULES ═══
# • Select EXACTLY 6 charts
# • At least 1 time-series chart (line or area)
# • At least 1 comparison chart (bar or grouped_bar)
# • At least 1 distribution chart (pie, donut, or histogram)
# • At least 1 relationship chart (scatter or heatmap)
# • No two charts should visualize the EXACT same data relationship

# ═══ RESPONSE FORMAT ═══
# Respond with ONLY this JSON:
# {{
#   "charts": [
#     {{
#       "chart_id": "CHART-001",
#       "chart_type": "bar",
#       "title": "Revenue by Product Category",
#       "x_axis": {{
#         "column": "ExactColumnName",
#         "label": "Human-readable label"
#       }},
#       "y_axis": {{
#         "column": "ExactColumnName",
#         "label": "Human-readable label",
#         "aggregation": "SUM"
#       }},
#       "group_by": null,
#       "sort_order": "descending",
#       "color_scheme": "categorical | sequential | diverging",
#       "business_insight": "Specific insight this chart reveals",
#       "actionable_recommendation": "Action to take based on this visualization"
#     }}
#   ]
# }}"""

#     return _llm_call_with_retry(prompt)


# # ═══════════════════════════════════════════════════════════════
# #  PHASE 8 — CHART DATA GENERATION (PANDAS-DRIVEN)
# # ═══════════════════════════════════════════════════════════════

# def _phase_8_generate_chart_data(df, charts_spec):
#     """
#     Phase 8: Generate actual aggregated data for each selected chart
#     using Pandas. Includes fallback strategies for empty results.
#     """
#     charts = charts_spec.get("charts", [])

#     for chart in charts:
#         chart["data"] = _generate_chart_data(df, chart)

#         # Fallback: if data is empty, try a count-based aggregation
#         if not chart["data"]:
#             x_col = chart.get("x_axis", {}).get("column", "")
#             if x_col in df.columns:
#                 try:
#                     vc = df[x_col].value_counts().head(10).reset_index()
#                     vc.columns = ['name', 'value']
#                     vc['name'] = vc['name'].astype(str)
#                     chart["data"] = _make_json_serializable(
#                         vc.to_dict(orient='records')
#                     )
#                     chart["y_axis"]["aggregation"] = "COUNT"
#                 except Exception:
#                     chart["data"] = []

#     return charts_spec


# # ═══════════════════════════════════════════════════════════════
# #  PHASE 9 — FINAL CONSOLIDATED OUTPUT PACKAGE
# # ═══════════════════════════════════════════════════════════════

# def _phase_9_consolidated_output(profile_data, computed_kpis, charts_with_data, df):
#     """
#     Phase 9: Generate executive-level insights and assemble the
#     complete dashboard-ready JSON package.
#     """
#     # Strip chart data from the prompt to avoid token overflow
#     charts_summary = []
#     for c in charts_with_data.get("charts", []):
#         charts_summary.append({
#             "title": c.get("title"),
#             "chart_type": c.get("chart_type"),
#             "business_insight": c.get("business_insight"),
#             "data_points": len(c.get("data", [])),
#         })

#     prompt = f"""You are the Solven Analytics Executive Summary Engine — Phase 9.

# ═══ ANALYSIS RESULTS ═══

# TOP 5 KPIs:
# {json.dumps([{{"name": k["kpi_name"], "value": k["kpi_value"], "insight": k["business_insight"]}} for k in computed_kpis.get("kpis", [])], indent=2)}

# TOP 6 CHARTS:
# {json.dumps(charts_summary, indent=2)}

# ═══ YOUR TASK ═══
# 1. Synthesize 3-5 KEY BUSINESS INSIGHTS derived from the KPIs and charts
# 2. Each insight must be ACTIONABLE — provide clear "so what" and "now what"
# 3. Rate each insight's impact level (HIGH / MEDIUM / LOW)
# 4. Note any data quality observations
# 5. Write a 2-3 sentence executive summary

# ═══ RESPONSE FORMAT ═══
# Respond with ONLY this JSON:
# {{
#   "key_business_insights": [
#     {{
#       "insight_id": "INS-001",
#       "insight": "Clear, specific insight statement backed by data",
#       "impact_level": "HIGH | MEDIUM | LOW",
#       "recommended_action": "Specific, actionable recommendation"
#     }}
#   ],
#   "data_quality_notes": [
#     "Any observations about data completeness, quality, or anomalies"
#   ],
#   "executive_summary": "2-3 sentence high-level summary of the entire analysis."
# }}"""

#     insights = _llm_call_with_retry(prompt)

#     # ── Assemble final output ──
#     dp = profile_data.get("dataset_profile", {})

#     # Detect date range
#     date_range = ""
#     temporal_cols = profile_data.get("_temporal_detected", [])
#     for col in temporal_cols:
#         if col in df.columns:
#             try:
#                 dates = pd.to_datetime(df[col], errors='coerce').dropna()
#                 if len(dates) > 0:
#                     date_range = (
#                         f"{dates.min().strftime('%Y-%m-%d')} to "
#                         f"{dates.max().strftime('%Y-%m-%d')}"
#                     )
#                     break
#             except Exception:
#                 pass

#     final = {
#         "solven_analytics_output": {
#             "version": "2.0",
#             "analysis_timestamp": datetime.datetime.now().isoformat(),

#             "dataset_summary": {
#                 "total_rows": dp.get("total_rows", len(df)),
#                 "total_columns": dp.get("total_columns", len(df.columns)),
#                 "domain": dp.get("domain", "General Business"),
#                 "date_range": date_range,
#                 "data_quality_score": dp.get("data_quality_score", "N/A"),
#                 "column_classifications": dp.get("column_classifications", {}),
#             },

#             "kpis": computed_kpis.get("kpis", []),

#             "charts": charts_with_data.get("charts", []),

#             "key_business_insights": insights.get("key_business_insights", []),

#             "executive_summary": insights.get("executive_summary", ""),

#             "data_quality_notes": insights.get("data_quality_notes", []),
#         }
#     }

#     return _make_json_serializable(final)


# # ═══════════════════════════════════════════════════════════════
# #  MAIN PIPELINE ENTRY POINT
# # ═══════════════════════════════════════════════════════════════
# def run_solven_analytics_pipeline(dataset_path):
#     """
#     Main orchestrator. Called by analytics_views.py.
#     Executes ALL 9 PHASES sequentially and returns the
#     complete consolidated JSON output package.
#     """
#     try:
#         print("=" * 60)
#         print("[Solven Analytics] Pipeline Starting...")
#         print("=" * 60)

#         # ════════════════════════════════════════
#         # DATA LOADING
#         # ════════════════════════════════════════

#         if dataset_path.endswith('.csv'):
#             try:
#                 df = pd.read_csv(dataset_path, encoding="utf-8")
#             except UnicodeDecodeError:
#                 df = pd.read_csv(dataset_path, encoding="latin1")

#         elif dataset_path.endswith(('.xlsx', '.xls')):
#             df = pd.read_excel(dataset_path)

#         else:
#             return {"error": "Unsupported file format. Please upload CSV or Excel (.xlsx/.xls)."}

#         if df.empty:
#             return {"error": "The uploaded file contains no data rows."}
#         # Clean column names (strip whitespace)
#         df.columns = df.columns.str.strip()

#         print(f"[Solven Analytics] Loaded: {len(df)} rows × {len(df.columns)} columns")

#         # ── Pre-compute numeric stats (used across multiple phases) ──
#         numeric_stats = {}
#         for col in df.select_dtypes(include=['number']).columns:
#             try:
#                 numeric_stats[col] = {
#                     "sum": float(df[col].sum()) if pd.notnull(df[col].sum()) else 0,
#                     "mean": round(float(df[col].mean()), 4) if pd.notnull(df[col].mean()) else 0,
#                     "median": float(df[col].median()) if pd.notnull(df[col].median()) else 0,
#                     "min": float(df[col].min()) if pd.notnull(df[col].min()) else 0,
#                     "max": float(df[col].max()) if pd.notnull(df[col].max()) else 0,
#                     "std": round(float(df[col].std()), 4) if pd.notnull(df[col].std()) else 0,
#                     "count": int(df[col].count()),
#                     "null_count": int(df[col].isnull().sum()),
#                     "unique_count": int(df[col].nunique()),
#                 }
#             except Exception as e:
#                 print(f"[Stats] Skipping column '{col}': {e}")

#         df_columns = list(df.columns)

#         # ════════════════════════════════════════
#         # PHASE 1 — Data Profiling
#         # ════════════════════════════════════════
#         print("\n[Phase 1] Data Profiling & Schema Understanding...")
#         profile_data = _phase_1_data_profiling(df)
#         if not profile_data or "dataset_profile" not in profile_data:
#             print("[Phase 1] WARNING: Profiling returned incomplete data, using fallback.")
#             profile_data = {
#                 "dataset_profile": {
#                     "total_rows": len(df),
#                     "total_columns": len(df.columns),
#                     "domain": "General",
#                     "data_quality_score": "N/A",
#                     "columns": [{"column_name": c, "classification": "metric" if pd.api.types.is_numeric_dtype(df[c]) else "dimension"} for c in df.columns],
#                     "column_classifications": {
#                         "metrics": list(df.select_dtypes(include=['number']).columns),
#                         "dimensions": list(df.select_dtypes(include=['object', 'category']).columns),
#                         "temporal": [],
#                         "identifiers": [],
#                     }
#                 },
#                 "_numeric_stats": numeric_stats,
#                 "_categorical_stats": {},
#                 "_all_columns": df_columns,
#                 "_temporal_detected": [],
#             }
#         print("[Phase 1] ✓ Complete")

#         # ════════════════════════════════════════
#         # PHASE 2 — KPI Generation
#         # ════════════════════════════════════════
#         print("[Phase 2] Exhaustive KPI Generation...")
#         generated_kpis = _phase_2_kpi_generation(profile_data, numeric_stats, df)
#         if not generated_kpis or not generated_kpis.get("generated_kpis"):
#             return {"error": "Phase 2 failed: Could not generate KPIs from this dataset."}
#         kpi_count = len(generated_kpis.get("generated_kpis", []))
#         print(f"[Phase 2] ✓ Generated {kpi_count} KPIs")

#         # ════════════════════════════════════════
#         # PHASE 3 — KPI Prioritization
#         # ════════════════════════════════════════
#         print("[Phase 3] KPI Prioritization & Selection...")
#         selected_kpis = _phase_3_kpi_prioritization(generated_kpis, profile_data)
#         if not selected_kpis or not selected_kpis.get("selected_kpis"):
#             return {"error": "Phase 3 failed: Could not prioritize KPIs."}
#         sel_count = len(selected_kpis.get("selected_kpis", []))
#         print(f"[Phase 3] ✓ Selected Top {sel_count} KPIs")

#         # ════════════════════════════════════════
#         # PHASE 4 — Formula Engineering
#         # ════════════════════════════════════════
#         print("[Phase 4] Formula Engineering & Computation Logic...")
#         kpi_formulas = _phase_4_formula_engineering(selected_kpis, numeric_stats, df_columns)
#         if not kpi_formulas or not kpi_formulas.get("kpis"):
#             return {"error": "Phase 4 failed: Could not engineer KPI formulas."}
#         print("[Phase 4] ✓ Complete")

#         # ════════════════════════════════════════
#         # PHASE 5 — KPI Computation (Pandas)
#         # ════════════════════════════════════════
#         print("[Phase 5] Computing KPI Values with Pandas...")
#         computed_kpis = _phase_5_compute_kpis(kpi_formulas, df, numeric_stats)
#         for kpi in computed_kpis.get("kpis", []):
#             print(f"  → {kpi['kpi_name']}: {kpi['kpi_value']}")
#         print("[Phase 5] ✓ Complete")

#         # ════════════════════════════════════════
#         # PHASE 6 — Chart Ideation
#         # ════════════════════════════════════════
#         print("[Phase 6] Chart Ideation & Visualization Mapping...")
#         chart_concepts = _phase_6_chart_ideation(profile_data, computed_kpis)
#         if not chart_concepts or not chart_concepts.get("chart_concepts"):
#             return {"error": "Phase 6 failed: Could not generate chart concepts."}
#         concept_count = len(chart_concepts.get("chart_concepts", []))
#         print(f"[Phase 6] ✓ Generated {concept_count} chart concepts")

#         # ════════════════════════════════════════
#         # PHASE 7 — Chart Selection
#         # ════════════════════════════════════════
#         print("[Phase 7] Chart Prioritization & Selection...")
#         selected_charts = _phase_7_chart_selection(chart_concepts)
#         if not selected_charts or not selected_charts.get("charts"):
#             return {"error": "Phase 7 failed: Could not select charts."}
#         chart_count = len(selected_charts.get("charts", []))
#         print(f"[Phase 7] ✓ Selected Top {chart_count} Charts")

#         # ════════════════════════════════════════
#         # PHASE 8 — Chart Data Generation (Pandas)
#         # ════════════════════════════════════════
#         print("[Phase 8] Generating Chart Data with Pandas...")
#         charts_with_data = _phase_8_generate_chart_data(df, selected_charts)
#         for chart in charts_with_data.get("charts", []):
#             dp_count = len(chart.get("data", []))
#             print(f"  → {chart.get('title', 'Untitled')}: {dp_count} data points")
#         print("[Phase 8] ✓ Complete")

#         # ════════════════════════════════════════
#         # PHASE 9 — Consolidated Output
#         # ════════════════════════════════════════
#         print("[Phase 9] Generating Final Consolidated Output...")
#         final_output = _phase_9_consolidated_output(
#             profile_data, computed_kpis, charts_with_data, df
#         )
#         print("[Phase 9] ✓ Complete")

#         print("\n" + "=" * 60)
#         print("[Solven Analytics] Pipeline Finished Successfully!")
#         print("=" * 60)

#         return final_output

#     except Exception as e:
#         print(f"\n[Solven Analytics] PIPELINE ERROR: {e}")
#         traceback.print_exc()
#         return {"error": f"Analytics pipeline failed: {str(e)}"}
    
# def rag_query(question):
#     return run_solven_analytics_pipeline(question)