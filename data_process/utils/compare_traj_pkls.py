#!/usr/bin/env python3
import argparse
import json
import math
import pickle
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np


def _is_numeric_array(arr: np.ndarray) -> bool:
    return np.issubdtype(arr.dtype, np.number) or np.issubdtype(arr.dtype, np.bool_)


def _to_array(value: Any) -> np.ndarray | None:
    if isinstance(value, np.ndarray):
        return value
    if isinstance(value, (list, tuple)):
        try:
            arr = np.asarray(value)
            return arr
        except Exception:
            return None
    return None


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def compare_values(a: Any, b: Any, rtol: float, atol: float) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "equal": False,
        "kind": "unknown",
        "detail": "",
    }

    arr_a = _to_array(a)
    arr_b = _to_array(b)

    if arr_a is not None and arr_b is not None:
        out["kind"] = "array"
        out["shape_a"] = list(arr_a.shape)
        out["shape_b"] = list(arr_b.shape)
        out["dtype_a"] = str(arr_a.dtype)
        out["dtype_b"] = str(arr_b.dtype)

        if arr_a.shape != arr_b.shape:
            out["detail"] = "shape_mismatch"
            return out

        if _is_numeric_array(arr_a) and _is_numeric_array(arr_b):
            arr_a = arr_a.astype(np.float64, copy=False)
            arr_b = arr_b.astype(np.float64, copy=False)

            exact_equal = np.array_equal(arr_a, arr_b, equal_nan=True)
            close_equal = np.allclose(arr_a, arr_b, rtol=rtol, atol=atol, equal_nan=True)

            diff = arr_a - arr_b
            finite_mask = np.isfinite(diff)
            if np.any(finite_mask):
                abs_diff = np.abs(diff[finite_mask])
                out["max_abs_diff"] = float(np.max(abs_diff))
                out["mean_abs_diff"] = float(np.mean(abs_diff))
                out["rmse"] = float(math.sqrt(np.mean(np.square(abs_diff))))
            else:
                out["max_abs_diff"] = None
                out["mean_abs_diff"] = None
                out["rmse"] = None

            out["exact_equal"] = bool(exact_equal)
            out["close_equal"] = bool(close_equal)
            out["equal"] = bool(close_equal)
            out["detail"] = "numeric"
            return out

        object_equal = np.array_equal(arr_a, arr_b)
        out["equal"] = bool(object_equal)
        out["detail"] = "non_numeric_array"
        return out

    scalar_a = _safe_float(a)
    scalar_b = _safe_float(b)
    if scalar_a is not None and scalar_b is not None:
        out["kind"] = "scalar"
        out["value_a"] = scalar_a
        out["value_b"] = scalar_b
        abs_diff = abs(scalar_a - scalar_b)
        out["abs_diff"] = abs_diff
        out["equal"] = bool(abs_diff <= (atol + rtol * abs(scalar_b)))
        out["detail"] = "numeric_scalar"
        return out

    out["kind"] = "python"
    out["equal"] = bool(a == b)
    out["value_a"] = repr(a)
    out["value_b"] = repr(b)
    out["detail"] = "python_eq"
    return out


def compare_pkls(path_a: Path, path_b: Path, rtol: float, atol: float) -> Dict[str, Any]:
    with open(path_a, "rb") as f:
        obj_a = pickle.load(f)
    with open(path_b, "rb") as f:
        obj_b = pickle.load(f)

    result: Dict[str, Any] = {
        "file_a": str(path_a),
        "file_b": str(path_b),
        "equal": True,
        "keys_only_in_a": [],
        "keys_only_in_b": [],
        "key_diffs": {},
    }

    if not isinstance(obj_a, dict) or not isinstance(obj_b, dict):
        cmp = compare_values(obj_a, obj_b, rtol=rtol, atol=atol)
        result["equal"] = cmp["equal"]
        result["root_compare"] = cmp
        return result

    keys_a = set(obj_a.keys())
    keys_b = set(obj_b.keys())
    result["keys_only_in_a"] = sorted(list(keys_a - keys_b))
    result["keys_only_in_b"] = sorted(list(keys_b - keys_a))

    if result["keys_only_in_a"] or result["keys_only_in_b"]:
        result["equal"] = False

    for key in sorted(list(keys_a & keys_b)):
        cmp = compare_values(obj_a[key], obj_b[key], rtol=rtol, atol=atol)
        if not cmp["equal"]:
            result["equal"] = False
            result["key_diffs"][key] = cmp

    return result


def collect_pkls(root: Path, target_name: str) -> Dict[str, Path]:
    matches: Dict[str, Path] = {}
    for p in root.rglob(target_name):
        rel = p.relative_to(root).as_posix()
        matches[rel] = p
    return matches


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare processed traj_data.pkl trees between two output roots.")
    parser.add_argument("--root-a", required=True, help="Path to first output root")
    parser.add_argument("--root-b", required=True, help="Path to second output root")
    parser.add_argument(
        "--target-name",
        default="traj_data.pkl",
        help="Filename to compare recursively (default: traj_data.pkl)",
    )
    parser.add_argument("--rtol", type=float, default=1e-5, help="Relative tolerance")
    parser.add_argument("--atol", type=float, default=1e-8, help="Absolute tolerance")
    parser.add_argument(
        "--max-report",
        type=int,
        default=30,
        help="Max number of mismatched files to print",
    )
    parser.add_argument(
        "--json-out",
        type=str,
        default=None,
        help="Optional path to save full JSON report",
    )

    args = parser.parse_args()

    root_a = Path(args.root_a).expanduser().resolve()
    root_b = Path(args.root_b).expanduser().resolve()

    if not root_a.exists() or not root_a.is_dir():
        raise ValueError(f"Invalid --root-a: {root_a}")
    if not root_b.exists() or not root_b.is_dir():
        raise ValueError(f"Invalid --root-b: {root_b}")

    map_a = collect_pkls(root_a, args.target_name)
    map_b = collect_pkls(root_b, args.target_name)

    rel_a = set(map_a.keys())
    rel_b = set(map_b.keys())

    only_a = sorted(list(rel_a - rel_b))
    only_b = sorted(list(rel_b - rel_a))
    common = sorted(list(rel_a & rel_b))

    mismatches: List[Dict[str, Any]] = []
    equal_count = 0

    for rel in common:
        cmp = compare_pkls(map_a[rel], map_b[rel], rtol=args.rtol, atol=args.atol)
        cmp["relative_path"] = rel
        if cmp["equal"]:
            equal_count += 1
        else:
            mismatches.append(cmp)

    summary = {
        "root_a": str(root_a),
        "root_b": str(root_b),
        "target_name": args.target_name,
        "count_a": len(rel_a),
        "count_b": len(rel_b),
        "common_count": len(common),
        "only_in_a_count": len(only_a),
        "only_in_b_count": len(only_b),
        "equal_common_count": equal_count,
        "mismatch_common_count": len(mismatches),
        "rtol": args.rtol,
        "atol": args.atol,
    }

    print("=== PKL Comparison Summary ===")
    for k, v in summary.items():
        print(f"{k}: {v}")

    if only_a:
        print("\nOnly in A (first 20):")
        for rel in only_a[:20]:
            print(f"  {rel}")

    if only_b:
        print("\nOnly in B (first 20):")
        for rel in only_b[:20]:
            print(f"  {rel}")

    if mismatches:
        print(f"\nMismatched common files (showing up to {args.max_report}):")
        for cmp in mismatches[: args.max_report]:
            rel = cmp["relative_path"]
            key_count = len(cmp.get("key_diffs", {}))
            only_a_keys = len(cmp.get("keys_only_in_a", []))
            only_b_keys = len(cmp.get("keys_only_in_b", []))
            print(f"  {rel} -> key_diffs={key_count}, " f"keys_only_in_a={only_a_keys}, keys_only_in_b={only_b_keys}")

    report = {
        "summary": summary,
        "only_in_a": only_a,
        "only_in_b": only_b,
        "mismatches": mismatches,
    }

    if args.json_out:
        out_path = Path(args.json_out).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"\nWrote JSON report: {out_path}")


if __name__ == "__main__":
    main()
