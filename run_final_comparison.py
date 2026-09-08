from __future__ import annotations

import argparse
import json
import math
import os
import random
import time
import uuid
import numpy as np
import pandas as pd
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence
from instance_generator import InstanceGenerator
from models.battery import Battery
from models.terminal import Terminal
from schedulers.ant_colony_scheduler import AntColonyScheduler
from schedulers.brkga_r_ls_scheduler import BRKGA_R_LS_Scheduler
from schedulers.genetic_algorithm_base_sheduler import GeneticAlgorithmScheduler
from schedulers.longest_time_processing_scheduler import LongestTimeProcessingScheduler
from schedulers.particle_swarm_scheduler import ParticleSwarmScheduler
from schedulers.smallest_initial_power_scheduler import SmallestInitialPowerScheduler
from schedulers.tabu_search_scheduler import TabuSearchScheduler
from schedulers.two_phase_ga_scheduler import TwoPhaseGAScheduler

ROOT = Path(__file__).resolve().parent
DEFAULT_METAHEURISTICS = ("ACO", "HPSO", "TS", "GA", "2PGA", "BRKGA-R-LS")
BASELINES = ("LPT", "SIP")
TIME_CHECKPOINTS_S = (1.0, 5.0, 15.0, 30.0, 60.0, 120.0)
DEFAULT_EVALUATION_COVERAGE = 0.90
PRESSURE_CLASS_ORDER = ("low", "medium", "high")
INSTANCE_SEED = 1_000
ALGORITHM_SEED = 1_000_000
RESULT_TOLERANCE = 1e-9

SCHEDULER_CLASSES = {
    "ACO": AntColonyScheduler,
    "HPSO": ParticleSwarmScheduler,
    "TS": TabuSearchScheduler,
    "GA": GeneticAlgorithmScheduler,
    "2PGA": TwoPhaseGAScheduler,
    "BRKGA-R-LS": BRKGA_R_LS_Scheduler,
    "LPT": LongestTimeProcessingScheduler,
    "SIP": SmallestInitialPowerScheduler,
}


@dataclass(frozen=True)
class ExperimentPaths:
    root: Path
    instance_bank: Path
    profile: Path
    raw_runs: Path
    exports: Path
    manifest: Path


class TimeLimitReached(Exception):
    pass


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument("--results-root", type=Path, default=ROOT / "comparison_results" / "final_comparison")
    parser.add_argument("--sizes", type=int, nargs="+", default=[20, 50, 100, 200, 500])
    parser.add_argument("--instances-per-size", type=int, default=6)
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--time-limit-s", type=float, default=120.0)
    parser.add_argument("--time-checkpoints-s",type=float,nargs="+",default=list(TIME_CHECKPOINTS_S))
    parser.add_argument("--evaluation-checkpoints", type=int, default=24)
    parser.add_argument("--evaluation-coverage", type=float, default=DEFAULT_EVALUATION_COVERAGE)
    parser.add_argument("--terminal-power-range", type=float, nargs=2, default=[90.0, 180.0])
    parser.add_argument("--energy-min-range", type=float, nargs=2, default=[80.0, 250.0])
    parser.add_argument("--energy-span-range", type=float, nargs=2, default=[500.0, 1000.0])
    parser.add_argument("--initial-power-min-range", type=float, nargs=2, default=[10.0, 25.0])
    parser.add_argument("--initial-power-span-range", type=float, nargs=2, default=[30.0, 55.0])

    parser.add_argument("--summarize-only", action="store_true")
    args = parser.parse_args(argv)

    if not 0 < args.evaluation_coverage <= 1:
        raise ValueError("--evaluation-coverage musi należeć do przedziału (0, 1].")

    args.results_root = args.results_root.resolve()
    args.sizes = tuple(args.sizes)
    checkpoints = {point for point in args.time_checkpoints_s if 0 < point <= args.time_limit_s}
    checkpoints.add(args.time_limit_s)
    args.time_checkpoints_s = tuple(sorted(checkpoints))
    return args

def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.replace(temporary, path)

def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)

def write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    frame.to_csv(temporary, index=False)
    try:
        for attempt in range(5):
            try:
                os.replace(temporary, path)
                return
            except PermissionError:
                if attempt == 4:
                    raise
                time.sleep(0.2 * (attempt + 1))
    finally:
        if temporary.exists():
            temporary.unlink()

def shuffled_values(count: int, low: float, high: float, rng: random.Random) -> list[float]:
    width = (high - low) / count
    values = [low + (index + rng.random()) * width for index in range(count)]
    rng.shuffle(values)
    return values

def instance_generation_settings(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "sizes": list(args.sizes),
        "instances_per_size": args.instances_per_size,
        "instance_seed": INSTANCE_SEED,
        "terminal_power_range": list(args.terminal_power_range),
        "energy_min_range": list(args.energy_min_range),
        "energy_span_range": list(args.energy_span_range),
        "initial_power_min_range": list(args.initial_power_min_range),
        "initial_power_span_range": list(args.initial_power_span_range),
    }

def pressure_class_counts(count: int) -> dict[str, int]:
    low = count // 3
    high = count // 3
    medium = count - low - high
    return {"low": low, "medium": medium, "high": high}

def assign_power_pressure_classes(instances: list[dict[str, Any]]) -> None:
    by_size: dict[int, list[dict[str, Any]]] = {}
    for instance in instances:
        by_size.setdefault(int(instance["size"]), []).append(instance)

    for group in by_size.values():
        ordered = sorted(
            group,
            key=lambda item: (
                float(item["features"]["mean_power_pressure_ratio"]),
                str(item["instance_id"]),
            ),
        )
        counts = pressure_class_counts(len(ordered))
        labels = (
            ["low"] * counts["low"]
            + ["medium"] * counts["medium"]
            + ["high"] * counts["high"]
        )
        for instance, label in zip(ordered, labels, strict=True):
            instance["power_pressure_class"] = label

def generate_instance_bank(args: argparse.Namespace) -> dict[str, Any]:
    instances: list[dict[str, Any]] = []
    for size_index, size in enumerate(args.sizes):
        group_seed = INSTANCE_SEED + (size_index + 1) * 1_000_000 + size
        group_rng = random.Random(group_seed)
        count = args.instances_per_size

        terminal_powers = shuffled_values(count, *args.terminal_power_range, group_rng)
        energy_mins = shuffled_values(count, *args.energy_min_range, group_rng)
        energy_spans = shuffled_values(count, *args.energy_span_range, group_rng)
        power_mins = shuffled_values(count, *args.initial_power_min_range, group_rng)
        power_spans = shuffled_values(count, *args.initial_power_span_range, group_rng)

        for instance_index in range(count):
            instance_seed = group_seed + instance_index
            terminal_power = terminal_powers[instance_index]
            energy_min = energy_mins[instance_index]
            energy_max = energy_min + energy_spans[instance_index]
            power_min = power_mins[instance_index]

            power_max = min(
                power_min + power_spans[instance_index],
                terminal_power * 0.90,
            )

            generator = InstanceGenerator(seed=instance_seed)
            generator.set_size(size)
            generator.set_energy_missing_range(energy_min, energy_max)
            generator.set_initial_power_consumption_range(power_min, power_max)
            batteries = generator.generate(terminal_power)

            instance_id = f"n{size:04d}_i{instance_index + 1:02d}"
            battery_rows = []
            for battery_index, battery in enumerate(batteries, start=1):
                battery.id = f"{instance_id}_b{battery_index:04d}"
                battery_rows.append(
                    {
                        "id": battery.id,
                        "energy_missing": float(battery.energy_missing),
                        "initial_power_consumption": float(battery.initial_power_consumption),
                    }
                )

            initial_powers = np.asarray(
                [row["initial_power_consumption"] for row in battery_rows], dtype=float
            )
            energies = np.asarray([row["energy_missing"] for row in battery_rows], dtype=float)
            instances.append(
                {
                    "instance_id": instance_id,
                    "size": size,
                    "instance_index": instance_index + 1,
                    "seed": instance_seed,
                    "terminal_max_power": float(terminal_power),
                    "generation_ranges": {
                        "energy_missing": [float(energy_min), float(energy_max)],
                        "initial_power_consumption": [float(power_min), float(power_max)],
                    },
                    "features": {
                        "mean_energy_missing": float(energies.mean()),
                        "std_energy_missing": float(energies.std(ddof=0)),
                        "mean_initial_power": float(initial_powers.mean()),
                        "std_initial_power": float(initial_powers.std(ddof=0)),
                        "mean_power_pressure_ratio": float(initial_powers.mean() / terminal_power),
                        "aggregate_power_pressure_ratio": float(initial_powers.sum() / terminal_power),
                    },
                    "batteries": battery_rows,
                }
            )

    assign_power_pressure_classes(instances)
    return {
        "generation_settings": instance_generation_settings(args),
        "instances": instances,
    }

def load_or_create_instance_bank(args: argparse.Namespace) -> tuple[Path, dict[str, Any]]:
    settings = instance_generation_settings(args)
    bank_path = args.results_root / f"instances_{args.instances_per_size}_per_size.json"
    if bank_path.exists():
        bank = read_json(bank_path)
        if bank.get("generation_settings") != settings:
            raise RuntimeError(f"Niezgodny manifest istniejącego banku: {bank_path}")
        return bank_path, bank

    bank = generate_instance_bank(args)
    write_json(bank_path, bank)
    return bank_path, bank

def build_batteries(instance: dict[str, Any]) -> list[Battery]:
    batteries = []
    for row in instance["batteries"]:
        battery = Battery(
            energy_missing=float(row["energy_missing"]),
            initial_power_consumption=float(row["initial_power_consumption"]),
        )
        battery.id = str(row["id"])
        batteries.append(battery)
    return batteries

def experiment_settings(
    args: argparse.Namespace,
    bank_path: Path,
) -> dict[str, Any]:
    return {
        "instance_bank": bank_path.name,
        "algorithms": list(DEFAULT_METAHEURISTICS),
        "baselines": list(BASELINES),
        "repetitions": args.repetitions,
        "time_limit_s": args.time_limit_s,
        "time_checkpoints_s": list(args.time_checkpoints_s),
        "evaluation_checkpoints": args.evaluation_checkpoints,
        "evaluation_coverage": args.evaluation_coverage,
        "algorithm_seed": ALGORITHM_SEED,
        "solution_limits": None,
    }


def prepare_paths(
    args: argparse.Namespace,
    bank_path: Path,
    settings: dict[str, Any],
) -> ExperimentPaths:
    profiles_root = args.results_root / "profiles"
    profiles_root.mkdir(parents=True, exist_ok=True)

    matching_profiles = []
    for manifest_path in profiles_root.glob("*/manifest.json"):
        try:
            manifest = read_json(manifest_path)
        except (OSError, json.JSONDecodeError):
            continue
        if manifest.get("experiment_settings") == settings:
            matching_profiles.append(manifest_path.parent)

    if matching_profiles:
        profile = max(matching_profiles, key=lambda path: path.stat().st_mtime)
    else:
        profile = profiles_root / f"run_{uuid.uuid4().hex[:8]}"

    paths = ExperimentPaths(
        root=args.results_root,
        instance_bank=bank_path,
        profile=profile,
        raw_runs=profile / "raw_runs",
        exports=profile / "exports",
        manifest=profile / "manifest.json",
    )
    if not paths.manifest.exists():
        manifest = {
            "profile_id": profile.name,
            "created_at_local": time.strftime("%Y-%m-%d %H:%M:%S"),
            "instance_bank_path": str(bank_path),
            "experiment_settings": settings,
        }
        write_json(paths.manifest, manifest)

    paths.raw_runs.mkdir(parents=True, exist_ok=True)
    paths.exports.mkdir(parents=True, exist_ok=True)
    return paths


class TrackedTerminal(Terminal):
    def __init__(self, max_power_capacity: float, time_limit_s: float | None):
        super().__init__(max_power_capacity=max_power_capacity)
        self.time_limit_s = time_limit_s
        self.started_at: float | None = None
        self.evaluation_count = 0
        self.best_makespan = float("inf")
        self.best_sequence_ids: list[str] = []
        self.improvements: list[dict[str, Any]] = []

    def start_clock(self) -> None:
        self.started_at = time.perf_counter()

    def elapsed(self) -> float:
        if self.started_at is None:
            return 0.0
        return time.perf_counter() - self.started_at

    def deadline_reached(self) -> bool:
        return self.time_limit_s is not None and self.elapsed() >= self.time_limit_s

    def process(self) -> float:
        if self.started_at is None:
            self.start_clock()
        if self.deadline_reached():
            raise TimeLimitReached

        sequence_ids = [battery.id for battery in self.batteries_to_load]
        makespan = super().process()
        self.evaluation_count += 1
        elapsed = self.elapsed()

        if makespan < self.best_makespan:
            self.best_makespan = float(makespan)
            self.best_sequence_ids = sequence_ids
            self.improvements.append(
                {
                    "time_elapsed_s": float(elapsed),
                    "solution_count": self.evaluation_count,
                    "makespan": float(makespan),
                }
            )

        if self.deadline_reached():
            raise TimeLimitReached
        return makespan

def raw_run_path(
    paths: ExperimentPaths,
    algorithm: str,
    instance_id: str,
    repetition: int,
) -> Path:
    return (
        paths.raw_runs
        / algorithm.lower().replace("-", "_")
        / f"{instance_id}_r{repetition:02d}.json"
    )


def configure_scheduler(
    algorithm: str,
    time_limit_s: float | None,
):
    scheduler_class = SCHEDULER_CLASSES[algorithm]
    if algorithm in BASELINES:
        return scheduler_class()
    return scheduler_class(max_time_s=time_limit_s)


def execute_run(
    args: argparse.Namespace,
    profile_id: str,
    instance: dict[str, Any],
    algorithm: str,
    repetition: int,
) -> dict[str, Any]:
    is_baseline = algorithm in BASELINES
    seed = ALGORITHM_SEED + int(instance["seed"]) * 10 + repetition
    random.seed(seed)
    np.random.seed(seed)

    time_limit = None if is_baseline else args.time_limit_s
    scheduler = configure_scheduler(algorithm, time_limit)
    terminal = TrackedTerminal(
        max_power_capacity=float(instance["terminal_max_power"]),
        time_limit_s=time_limit,
    )
    batteries = build_batteries(instance)

    terminal.start_clock()
    termination_reason = "completed"
    try:
        scheduler.fit(terminal, batteries)
    except TimeLimitReached:
        termination_reason = "time_limit"

    elapsed = terminal.elapsed()
    if terminal.evaluation_count == 0 or not math.isfinite(terminal.best_makespan):
        raise RuntimeError(f"{algorithm} nie ocenił żadnego rozwiązania.")

    if (
        not is_baseline
        and termination_reason == "completed"
        and elapsed >= args.time_limit_s * 0.98
    ):
        termination_reason = "time_limit"

    if not is_baseline and termination_reason != "time_limit":
        if elapsed < args.time_limit_s * 0.98:
            raise RuntimeError(
                f"{algorithm} zakończył pracę po {elapsed:.3f}s, przed limitem "
                f"{args.time_limit_s:.3f}s."
            )

    return {
        "profile_id": profile_id,
        "status": "ok",
        "algorithm": algorithm,
        "instance_id": instance["instance_id"],
        "repetition": repetition,
        "makespan": float(terminal.best_makespan),
        "execution_time_s": float(elapsed),
        "time_overrun_s": float(max(0.0, elapsed - time_limit)) if time_limit else 0.0,
        "solution_count": int(terminal.evaluation_count),
        "termination_reason": termination_reason,
        "hit_time_limit": termination_reason == "time_limit",
        "best_sequence_ids": terminal.best_sequence_ids,
        "improvements": terminal.improvements,
    }


def completed_run(
    path: Path,
    profile_id: str,
) -> bool:
    if not path.exists():
        return False
    try:
        payload = read_json(path)
    except (OSError, EOFError, json.JSONDecodeError):
        return False
    return payload.get("status") == "ok" and payload.get("profile_id") == profile_id


def enumerate_cases(
    args: argparse.Namespace,
    bank: dict[str, Any],
) -> list[tuple[dict[str, Any], str, int]]:
    cases: list[tuple[dict[str, Any], str, int]] = []
    for instance in bank["instances"]:
        cases.extend((instance, baseline, 0) for baseline in BASELINES)
        for repetition in range(1, args.repetitions + 1):
            cases.extend(
                (instance, algorithm, repetition)
                for algorithm in DEFAULT_METAHEURISTICS
            )
    return cases

def run_experiment(
    args: argparse.Namespace,
    bank: dict[str, Any],
    paths: ExperimentPaths,
) -> None:
    manifest = read_json(paths.manifest)
    profile_id = manifest["profile_id"]
    cases = enumerate_cases(args, bank)
    already_done = sum(
        completed_run(raw_run_path(paths, algorithm, instance["instance_id"], repetition), profile_id)
        for instance, algorithm, repetition in cases
    )
    print(
        f"Profil: {paths.profile.name}\n"
        f"Instancje: {len(bank['instances'])}\n"
        f"Próby: {len(cases)} (gotowe: {already_done}, pozostało: {len(cases) - already_done})\n"
        f"Wyniki: {paths.profile}"
    )

    for case_index, (instance, algorithm, repetition) in enumerate(cases, start=1):
        destination = raw_run_path(paths, algorithm, instance["instance_id"], repetition)
        if completed_run(destination, profile_id):
            continue

        print(
            f"[{case_index}/{len(cases)}] {algorithm} | {instance['instance_id']} "
            f"| powtórzenie={repetition}"
        )
        try:
            payload = execute_run(
                args=args,
                profile_id=profile_id,
                instance=instance,
                algorithm=algorithm,
                repetition=repetition,
            )
            write_json(destination, payload)
            print(
                f"  makespan={payload['makespan']:.6f} | "
                f"wykonanych ocen rozwiązań={payload['solution_count']} | "
                f"czas={payload['execution_time_s']:.3f}s"
            )
        except KeyboardInterrupt:
            print("\nPrzerwano przez użytkownika. Zakończone próby są zapisane.")
            raise
        except Exception as exc:
            print(f"  BŁĄD: {type(exc).__name__}: {exc}")
            raise


def load_raw_runs(paths: ExperimentPaths) -> list[dict[str, Any]]:
    profile_id = read_json(paths.manifest)["profile_id"]
    rows = []
    for path in sorted(paths.raw_runs.rglob("*.json")):
        try:
            payload = read_json(path)
        except (OSError, EOFError, json.JSONDecodeError):
            continue
        if payload.get("status") == "ok" and payload.get("profile_id") == profile_id:
            rows.append(payload)
    return rows


def instance_frame(bank: dict[str, Any]) -> pd.DataFrame:
    instance_rows = []
    for instance in bank["instances"]:
        features = instance["features"]
        instance_rows.append(
            {
                "instance_id": instance["instance_id"],
                "size": instance["size"],
                "instance_index": instance["instance_index"],
                "instance_seed": instance["seed"],
                "power_pressure_class": instance.get("power_pressure_class"),
                "terminal_max_power": instance["terminal_max_power"],
                "energy_min": instance["generation_ranges"]["energy_missing"][0],
                "energy_max": instance["generation_ranges"]["energy_missing"][1],
                "initial_power_min": instance["generation_ranges"]
                ["initial_power_consumption"][0],
                "initial_power_max": instance["generation_ranges"]
                ["initial_power_consumption"][1],
                **features,
            }
        )
    instances = pd.DataFrame(instance_rows)

    if instances["power_pressure_class"].isna().any():
        for _, group in instances.groupby("size", observed=True):
            ordered_indices = group.sort_values(
                ["mean_power_pressure_ratio", "instance_id"]
            ).index.tolist()
            counts = pressure_class_counts(len(ordered_indices))
            labels = (
                ["low"] * counts["low"]
                + ["medium"] * counts["medium"]
                + ["high"] * counts["high"]
            )
            instances.loc[ordered_indices, "power_pressure_class"] = labels
    return instances


def is_tie(left: float, right: float) -> bool:
    return math.isclose(
        left,
        right,
        rel_tol=RESULT_TOLERANCE,
        abs_tol=RESULT_TOLERANCE,
    )


def best_result_at(improvements: Sequence[dict[str, Any]], axis: str, checkpoint: float) -> tuple[float, float, int] | None:
    eligible = [point for point in improvements if float(point[axis]) <= checkpoint]
    if not eligible:
        return None
    point = eligible[-1]
    return (
        float(point["makespan"]),
        float(point["time_elapsed_s"]),
        int(point["solution_count"]),
    )


def time_to_target(
    improvements: Sequence[dict[str, Any]],
    target: float,
) -> tuple[float | None, int | None]:
    for point in improvements:
        if float(point["makespan"]) <= target or is_tie(float(point["makespan"]), target):
            return float(point["time_elapsed_s"]), int(point["solution_count"])
    return None, None


def rpd(makespan: float, reference: float) -> float:
    return 100.0 * (makespan - reference) / reference


def auc_rpd(improvements: Sequence[dict[str, Any]], best_known: float, time_limit_s: float) -> float:
    if not improvements:
        return float("nan")
    ordered = sorted(improvements, key=lambda point: float(point["time_elapsed_s"]))
    current_rpd = rpd(float(ordered[0]["makespan"]), best_known)
    previous_time = 0.0
    area = 0.0
    for point in ordered[1:]:
        point_time = min(float(point["time_elapsed_s"]), time_limit_s)
        if point_time <= previous_time:
            current_rpd = rpd(float(point["makespan"]), best_known)
            continue
        area += current_rpd * (point_time - previous_time)
        previous_time = point_time
        current_rpd = rpd(float(point["makespan"]), best_known)
        if previous_time >= time_limit_s:
            break
    if previous_time < time_limit_s:
        area += current_rpd * (time_limit_s - previous_time)
    return area / time_limit_s


def safe_quantile(series: pd.Series, probability: float) -> float:
    clean = pd.to_numeric(series)
    return float(clean.quantile(probability)) if not clean.empty else float("nan")


def aggregate_final(frame: pd.DataFrame, group_columns: Sequence[str]) -> pd.DataFrame:
    rows = []
    grouped: Iterable[tuple[Any, pd.DataFrame]]
    if group_columns:
        grouped = frame.groupby(list(group_columns), observed=True, dropna=False)
    else:
        grouped = [((), frame)]

    for key, group in grouped:
        keys = key if isinstance(key, tuple) else (key,)
        row = dict(zip(group_columns, keys))
        q1 = safe_quantile(group["rpd"], 0.25)
        q3 = safe_quantile(group["rpd"], 0.75)
        successful_times_0_1 = group.loc[
            group["reached_0_1pct"], "time_to_0_1pct_s"
        ]
        successful_evaluations_0_1 = group.loc[
            group["reached_0_1pct"], "evaluations_to_0_1pct"
        ]
        successful_times_1 = group.loc[group["reached_1pct"], "time_to_1pct_s"]
        successful_evaluations_1 = group.loc[
            group["reached_1pct"], "evaluations_to_1pct"
        ]
        row.update(
            {
                "runs": int(len(group)),
                "instances": int(group["instance_id"].nunique()),
                "arpd": float(group["rpd"].mean()),
                "median_rpd": float(group["rpd"].median()),
                "q1_rpd": q1,
                "q3_rpd": q3,
                "iqr_rpd": q3 - q1,
                "std_rpd": float(group["rpd"].std(ddof=1)) if len(group) > 1 else 0.0,
                "bks_hits": int(group["hit_bks"].sum()),
                "bks_hit_rate_pct": 100.0 * float(group["hit_bks"].mean()),
                "within_0_1pct_runs": int(group["reached_0_1pct"].sum()),
                "within_0_1pct_rate_pct": 100.0
                * float(group["reached_0_1pct"].mean()),
                "median_time_to_0_1pct_s_among_successes": (
                    float(successful_times_0_1.median())
                    if not successful_times_0_1.empty
                    else float("nan")
                ),
                "not_reached_0_1pct_runs": int((~group["reached_0_1pct"]).sum()),
                "median_evaluations_to_0_1pct_among_successes": (
                    float(successful_evaluations_0_1.median())
                    if not successful_evaluations_0_1.empty
                    else float("nan")
                ),
                "within_1pct_runs": int(group["reached_1pct"].sum()),
                "within_1pct_rate_pct": 100.0 * float(group["reached_1pct"].mean()),
                "median_time_to_1pct_s_among_successes": (
                    float(successful_times_1.median())
                    if not successful_times_1.empty
                    else float("nan")
                ),
                "not_reached_1pct_runs": int((~group["reached_1pct"]).sum()),
                "median_evaluations_to_1pct_among_successes": (
                    float(successful_evaluations_1.median())
                    if not successful_evaluations_1.empty
                    else float("nan")
                ),
                "median_solution_count": float(group["solution_count"].median()),
                "median_solutions_per_second": float(group["solutions_per_second"].median()),
                "median_auc_rpd_time": float(group["auc_rpd_time"].median()),
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def aggregate_checkpoint(frame: pd.DataFrame, group_columns: Sequence[str]) -> pd.DataFrame:
    rows = []
    for key, group in frame.groupby(list(group_columns), observed=True, dropna=False):
        keys = key if isinstance(key, tuple) else (key,)
        q1 = safe_quantile(group["rpd"], 0.25)
        q3 = safe_quantile(group["rpd"], 0.75)
        row = dict(zip(group_columns, keys))
        row.update(
            {
                "observations": int(len(group)),
                "solution_available_rate_pct": 100.0
                * float(group["has_solution"].mean()),
                "arpd": float(group["rpd"].mean()),
                "median_rpd": float(group["rpd"].median()),
                "q1_rpd": q1,
                "q3_rpd": q3,
                "iqr_rpd": q3 - q1,
                "std_rpd": float(group["rpd"].std(ddof=1)) if len(group) > 1 else 0.0,
                "bks_hits": int(group["hit_bks"].sum()),
                "bks_hit_rate_pct": 100.0 * float(group["hit_bks"].mean()),
                "within_0_1pct_observations": int(group["within_0_1pct"].sum()),
                "within_0_1pct_rate_pct": 100.0
                * float(group["within_0_1pct"].mean()),
                "within_1pct_observations": int(group["within_1pct"].sum()),
                "within_1pct_rate_pct": 100.0 * float(group["within_1pct"].mean()),
                "beats_or_ties_naive_rate_pct": 100.0
                * float(group["beats_or_ties_naive"].mean()),
                "strictly_beats_naive_rate_pct": 100.0
                * float(group["strictly_beats_naive"].mean()),
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def evaluation_budgets(runs: pd.DataFrame, size: int, count: int, coverage: float = DEFAULT_EVALUATION_COVERAGE) -> list[int]:
    size_runs = runs[(runs["size"] == size) & (~runs["is_baseline"])]
    if size_runs.empty:
        return []

    quantile_probability = 1.0 - coverage
    per_algorithm_limits = size_runs.groupby("algorithm", observed=True)[
        "solution_count"
    ].quantile(quantile_probability, interpolation="higher")
    common_max = int(per_algorithm_limits.min())
    if common_max <= 1:
        return [1]
    raw = np.geomspace(1, common_max, num=count)
    return sorted(set(int(round(value)) for value in raw) | {1, common_max})


def build_ga_comparison(runs: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if "GA" not in set(runs["algorithm"]):
        return pd.DataFrame(), pd.DataFrame()
    comparison_rows = []
    ga_columns = [
        "instance_id",
        "repetition",
        "size",
        "power_pressure_class",
        "rpd",
        "reached_0_1pct",
        "time_to_0_1pct_s",
        "evaluations_to_0_1pct",
        "reached_1pct",
        "time_to_1pct_s",
        "evaluations_to_1pct",
    ]
    ga = runs[runs["algorithm"] == "GA"][ga_columns].copy()
    for variant in ("2PGA", "BRKGA-R-LS"):
        variant_frame = runs[runs["algorithm"] == variant][ga_columns].copy()
        if variant_frame.empty:
            continue
        paired = ga.merge(
            variant_frame,
            on=["instance_id", "repetition", "size", "power_pressure_class"],
            suffixes=("_ga", "_variant"),
        )
        for row in paired.itertuples(index=False):
            delta = float(row.rpd_ga - row.rpd_variant)
            outcome = "tie" if is_tie(row.rpd_ga, row.rpd_variant) else (
                "variant_win" if delta > 0 else "ga_win"
            )
            comparison_rows.append(
                {
                    "variant": variant,
                    "instance_id": row.instance_id,
                    "repetition": row.repetition,
                    "size": row.size,
                    "power_pressure_class": row.power_pressure_class,
                    "ga_rpd": row.rpd_ga,
                    "variant_rpd": row.rpd_variant,
                    "rpd_improvement_over_ga": delta,
                    "outcome": outcome,
                    "ga_reached_0_1pct": row.reached_0_1pct_ga,
                    "variant_reached_0_1pct": row.reached_0_1pct_variant,
                    "ga_time_to_0_1pct_s": row.time_to_0_1pct_s_ga,
                    "variant_time_to_0_1pct_s": row.time_to_0_1pct_s_variant,
                    "ga_evaluations_to_0_1pct": row.evaluations_to_0_1pct_ga,
                    "variant_evaluations_to_0_1pct": row.evaluations_to_0_1pct_variant,
                    "ga_reached_1pct": row.reached_1pct_ga,
                    "variant_reached_1pct": row.reached_1pct_variant,
                    "ga_time_to_1pct_s": row.time_to_1pct_s_ga,
                    "variant_time_to_1pct_s": row.time_to_1pct_s_variant,
                    "ga_evaluations_to_1pct": row.evaluations_to_1pct_ga,
                    "variant_evaluations_to_1pct": row.evaluations_to_1pct_variant,
                }
            )
    pairs = pd.DataFrame(comparison_rows)
    if pairs.empty:
        return pairs, pd.DataFrame()

    return pairs, summarize_ga_pairs(pairs, ["variant"])


def summarize_ga_pairs(pairs: pd.DataFrame,group_columns: Sequence[str]) -> pd.DataFrame:
    if pairs.empty:
        return pd.DataFrame()

    summary_rows = []
    for key, group in pairs.groupby(list(group_columns), observed=True, dropna=False):
        keys = key if isinstance(key, tuple) else (key,)
        summary = dict(zip(group_columns, keys))
        both_reached_0_1 = group[
            group["ga_reached_0_1pct"] & group["variant_reached_0_1pct"]
        ]
        both_reached = group[group["ga_reached_1pct"] & group["variant_reached_1pct"]]
        summary.update(
            {
                "pairs": len(group),
                "median_rpd_improvement_over_ga": group["rpd_improvement_over_ga"].median(),
                "mean_rpd_improvement_over_ga": group["rpd_improvement_over_ga"].mean(),
                "variant_win_rate_pct": 100.0 * (group["outcome"] == "variant_win").mean(),
                "tie_rate_pct": 100.0 * (group["outcome"] == "tie").mean(),
                "ga_win_rate_pct": 100.0 * (group["outcome"] == "ga_win").mean(),
                "within_0_1pct_rate_change_pp": 100.0
                * (
                    group["variant_reached_0_1pct"].mean()
                    - group["ga_reached_0_1pct"].mean()
                ),
                "pairs_where_both_reached_0_1pct": len(both_reached_0_1),
                "median_time_saved_to_0_1pct_s_when_both_reached": (
                    (
                        both_reached_0_1["ga_time_to_0_1pct_s"]
                        - both_reached_0_1["variant_time_to_0_1pct_s"]
                    ).median()
                    if not both_reached_0_1.empty
                    else float("nan")
                ),
                "median_evaluations_saved_to_0_1pct_when_both_reached": (
                    (
                        both_reached_0_1["ga_evaluations_to_0_1pct"]
                        - both_reached_0_1["variant_evaluations_to_0_1pct"]
                    ).median()
                    if not both_reached_0_1.empty
                    else float("nan")
                ),
                "within_1pct_rate_change_pp": 100.0
                * (group["variant_reached_1pct"].mean() - group["ga_reached_1pct"].mean()),
                "pairs_where_both_reached_1pct": len(both_reached),
                "median_time_saved_to_1pct_s_when_both_reached": (
                    (both_reached["ga_time_to_1pct_s"] - both_reached["variant_time_to_1pct_s"]).median()
                    if not both_reached.empty
                    else float("nan")
                ),
                "median_evaluations_saved_to_1pct_when_both_reached": (
                    (
                        both_reached["ga_evaluations_to_1pct"]
                        - both_reached["variant_evaluations_to_1pct"]
                    ).median()
                    if not both_reached.empty
                    else float("nan")
                ),
            }
        )
        summary_rows.append(summary)
    return pd.DataFrame(summary_rows)


def build_exports(args: argparse.Namespace, bank: dict[str, Any], paths: ExperimentPaths) -> None:
    payloads = load_raw_runs(paths)
    instances = instance_frame(bank)
    write_csv(instances, paths.exports / "instances.csv")
    if not payloads:
        print("Brak ukończonych prób do podsumowania.")
        return

    run_rows = []
    payload_by_key: dict[tuple[str, str, int], dict[str, Any]] = {}
    for payload in payloads:
        key = (payload["algorithm"], payload["instance_id"], int(payload["repetition"]))
        payload_by_key[key] = payload
        run_rows.append(
            {key: value for key, value in payload.items() if key not in {"improvements", "best_sequence_ids"}}
        )

    runs = pd.DataFrame(run_rows)
    runs = runs.merge(
        instances[["instance_id", "size", "power_pressure_class"]],
        on="instance_id",
        how="left",
    )
    runs["is_baseline"] = runs["algorithm"].isin(BASELINES)
    runs["solutions_per_second"] = runs["solution_count"] / runs["execution_time_s"]
    bks = (
        runs.groupby("instance_id", as_index=False, observed=True)["makespan"]
        .min()
        .rename(columns={"makespan": "best_known_makespan"})
    )
    naive = (
        runs[runs["is_baseline"]]
        .groupby("instance_id", as_index=False, observed=True)["makespan"]
        .min()
        .rename(columns={"makespan": "best_naive_makespan"})
    )
    bks = bks.merge(naive, on="instance_id", how="left")
    runs = runs.merge(bks, on="instance_id", how="left")
    runs["rpd"] = 100.0 * (
        runs["makespan"] - runs["best_known_makespan"]
    ) / runs["best_known_makespan"]
    runs["hit_bks"] = np.isclose(
        runs["makespan"],
        runs["best_known_makespan"],
        rtol=RESULT_TOLERANCE,
        atol=RESULT_TOLERANCE,
    )
    runs["within_0_1pct"] = runs["makespan"] <= 1.001 * runs["best_known_makespan"]
    runs["within_1pct"] = runs["makespan"] <= 1.01 * runs["best_known_makespan"]

    target_times_0_1 = []
    target_evaluations_0_1 = []
    target_times_1 = []
    target_evaluations_1 = []
    auc_values = []
    for row in runs.itertuples(index=False):
        payload = payload_by_key[(row.algorithm, row.instance_id, int(row.repetition))]
        target_0_1 = 1.001 * float(row.best_known_makespan)
        reached_time_0_1, reached_evaluations_0_1 = time_to_target(
            payload["improvements"], target_0_1
        )
        target_times_0_1.append(reached_time_0_1)
        target_evaluations_0_1.append(reached_evaluations_0_1)
        target_1 = 1.01 * float(row.best_known_makespan)
        reached_time_1, reached_evaluations_1 = time_to_target(
            payload["improvements"], target_1
        )
        target_times_1.append(reached_time_1)
        target_evaluations_1.append(reached_evaluations_1)
        auc_values.append(
            auc_rpd(payload["improvements"], float(row.best_known_makespan), args.time_limit_s)
            if not row.is_baseline
            else float("nan")
        )
    runs["time_to_0_1pct_s"] = target_times_0_1
    runs["evaluations_to_0_1pct"] = target_evaluations_0_1
    runs["reached_0_1pct"] = runs["time_to_0_1pct_s"].notna()
    runs["time_to_1pct_s"] = target_times_1
    runs["evaluations_to_1pct"] = target_evaluations_1
    runs["reached_1pct"] = runs["time_to_1pct_s"].notna()
    runs["auc_rpd_time"] = auc_values

    ordered_run_columns = [
        "algorithm", "is_baseline", "instance_id", "size", "power_pressure_class",
        "repetition", "makespan",
        "best_known_makespan", "best_naive_makespan", "rpd", "hit_bks",
        "within_0_1pct", "reached_0_1pct", "time_to_0_1pct_s",
        "evaluations_to_0_1pct",
        "within_1pct", "reached_1pct", "time_to_1pct_s", "evaluations_to_1pct",
        "execution_time_s", "time_overrun_s", "solution_count", "solutions_per_second",
        "auc_rpd_time",
        "termination_reason", "hit_time_limit",
    ]
    remaining = [column for column in runs.columns if column not in ordered_run_columns]
    runs = runs[ordered_run_columns + remaining].sort_values(
        ["instance_id", "algorithm", "repetition"]
    )
    write_csv(runs, paths.exports / "runs.csv")

    meta_runs = runs[~runs["is_baseline"]].copy()
    write_csv(
        aggregate_final(meta_runs, ["algorithm"]),
        paths.exports / "summary_final_overall.csv",
    )
    write_csv(
        aggregate_final(meta_runs, ["algorithm", "size"]),
        paths.exports / "summary_final_by_size.csv",
    )
    write_csv(
        aggregate_final(meta_runs, ["algorithm", "power_pressure_class"]),
        paths.exports / "summary_final_by_power_pressure.csv",
    )
    write_csv(
        aggregate_final(meta_runs, ["algorithm", "size", "power_pressure_class"]),
        paths.exports / "summary_final_by_size_and_power_pressure.csv",
    )

    time_rows = []
    for row in meta_runs.itertuples(index=False):
        payload = payload_by_key[(row.algorithm, row.instance_id, int(row.repetition))]
        for checkpoint in args.time_checkpoints_s:
            best_result = best_result_at(payload["improvements"], "time_elapsed_s", checkpoint)
            if best_result is None:
                time_rows.append(
                    {
                        "algorithm": row.algorithm,
                        "instance_id": row.instance_id,
                        "size": row.size,
                        "power_pressure_class": row.power_pressure_class,
                        "repetition": row.repetition,
                        "checkpoint_s": checkpoint,
                        "best_result_time_s": float("nan"),
                        "solution_count": 0,
                        "makespan": float("nan"),
                        "rpd": float("nan"),
                        "has_solution": False,
                        "hit_bks": False,
                        "within_0_1pct": False,
                        "within_1pct": False,
                        "beats_or_ties_naive": False,
                        "strictly_beats_naive": False,
                    }
                )
                continue
            makespan, actual_time, solution_count = best_result
            time_rows.append(
                {
                    "algorithm": row.algorithm,
                    "instance_id": row.instance_id,
                    "size": row.size,
                    "power_pressure_class": row.power_pressure_class,
                    "repetition": row.repetition,
                    "checkpoint_s": checkpoint,
                    "best_result_time_s": actual_time,
                    "solution_count": solution_count,
                    "makespan": makespan,
                    "rpd": rpd(makespan, row.best_known_makespan),
                    "has_solution": True,
                    "hit_bks": is_tie(makespan, row.best_known_makespan),
                    "within_0_1pct": makespan <= 1.001 * row.best_known_makespan,
                    "within_1pct": makespan <= 1.01 * row.best_known_makespan,
                    "beats_or_ties_naive": makespan <= row.best_naive_makespan or is_tie(makespan, row.best_naive_makespan),
                    "strictly_beats_naive": makespan < row.best_naive_makespan and not is_tie(makespan, row.best_naive_makespan),
                }
            )
    time_frame = pd.DataFrame(time_rows)
    write_csv(time_frame, paths.exports / "time_checkpoint_runs.csv")

    evaluation_rows = []
    for size in sorted(meta_runs["size"].unique()):
        budgets = evaluation_budgets(
            meta_runs,
            int(size),
            args.evaluation_checkpoints,
            args.evaluation_coverage,
        )
        size_runs = meta_runs[meta_runs["size"] == size]
        for row in size_runs.itertuples(index=False):
            payload = payload_by_key[(row.algorithm, row.instance_id, int(row.repetition))]
            for budget in budgets:
                if int(row.solution_count) < budget:
                    continue
                best_result = best_result_at(payload["improvements"], "solution_count", budget)
                if best_result is None:
                    continue
                makespan, actual_time, actual_count = best_result
                evaluation_rows.append(
                    {
                        "algorithm": row.algorithm,
                        "instance_id": row.instance_id,
                        "size": row.size,
                        "power_pressure_class": row.power_pressure_class,
                        "repetition": row.repetition,
                        "evaluation_budget": budget,
                        "run_solution_count": int(row.solution_count),
                        "best_result_solution_count": actual_count,
                        "best_result_time_s": actual_time,
                        "makespan": makespan,
                        "rpd": rpd(makespan, row.best_known_makespan),
                        "has_solution": True,
                        "hit_bks": is_tie(makespan, row.best_known_makespan),
                        "within_0_1pct": makespan <= 1.001 * row.best_known_makespan,
                        "within_1pct": makespan <= 1.01 * row.best_known_makespan,
                        "beats_or_ties_naive": makespan <= row.best_naive_makespan or is_tie(makespan, row.best_naive_makespan),
                        "strictly_beats_naive": makespan < row.best_naive_makespan and not is_tie(makespan, row.best_naive_makespan),
                    }
                )
    evaluation_frame = pd.DataFrame(evaluation_rows)
    if not evaluation_frame.empty:
        evaluation_summary = aggregate_checkpoint(
            evaluation_frame,
            ["algorithm", "size", "evaluation_budget"],
        )
        expected = (
            meta_runs.groupby(["algorithm", "size"], observed=True)
            .size()
            .rename("eligible_runs_total")
            .reset_index()
        )
        evaluation_summary = evaluation_summary.merge(
            expected, on=["algorithm", "size"], how="left"
        )
        evaluation_summary["coverage_rate_pct"] = (
            100.0
            * evaluation_summary["observations"]
            / evaluation_summary["eligible_runs_total"]
        )
        write_csv(
            evaluation_summary,
            paths.exports / "summary_evaluation_checkpoints.csv",
        )

    ga_pairs, ga_summary = build_ga_comparison(meta_runs)
    write_csv(ga_pairs, paths.exports / "ga_extension_pairs.csv")
    write_csv(ga_summary, paths.exports / "summary_ga_extensions.csv")

    progress = {
        "profile": paths.profile.name,
        "saved_raw_runs": len(payloads),
        "expected_raw_runs": len(enumerate_cases(args, bank)),
        "completion_pct": 100.0 * len(payloads) / len(enumerate_cases(args, bank)),
        "updated_at_local": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    write_json(paths.profile / "progress.json", progress)
    print(
        f"Eksporty odświeżone: {paths.exports} "
        f"({len(payloads)}/{progress['expected_raw_runs']} prób)"
    )


def print_plan(args: argparse.Namespace, bank: dict[str, Any], paths: ExperimentPaths) -> None:
    meta_runs = len(bank["instances"]) * len(DEFAULT_METAHEURISTICS) * args.repetitions
    baseline_runs = len(bank["instances"]) * len(BASELINES)
    worst_case_hours = meta_runs * args.time_limit_s / 3600.0
    print(
        "\nPlan eksperymentu\n"
        f"  bank instancji: {paths.instance_bank}\n"
        f"  profil wyników: {paths.profile}\n"
        f"  rozmiary: {args.sizes}\n"
        f"  instancje: {len(bank['instances'])}\n"
        f"  powtórzenia: {args.repetitions}\n"
        f"  metaheurystyki: {DEFAULT_METAHEURISTICS}\n"
        f"  limit: {args.time_limit_s:g}s\n"
        f"  pokrycie wspólnego budżetu ocen: {100 * args.evaluation_coverage:g}%\n"
        f"  próby metaheurystyk: {meta_runs}\n"
        f"  próby metod naiwnych: {baseline_runs}\n"
        f"  maksymalny czas sekwencyjny: {worst_case_hours:.2f}h\n"
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    args.results_root.mkdir(parents=True, exist_ok=True)
    bank_path, bank = load_or_create_instance_bank(args)
    settings = experiment_settings(args, bank_path)
    paths = prepare_paths(args, bank_path, settings)
    print_plan(args, bank, paths)

    if not args.summarize_only:
        run_experiment(args, bank, paths)
    build_exports(args, bank, paths)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
