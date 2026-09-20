"""Unit tests for Environmental Emissions and Fuel Consumption Modeling.

Tests:
- Zero idle delay produces zero emissions.
- Exact deterministic mathematical calculation of fuel and CO2.
- Custom EmissionsConfig parameterization.
- EmissionsMetrics serialization and bounds.
"""

import pytest
import numpy as np
from simulation.emissions import EmissionsConfig, EmissionsMetrics, calculate_emissions


def test_zero_traffic_emissions():
    """Verify zero idle time produces exactly zero fuel and CO2."""
    res = calculate_emissions(idle_vehicle_seconds=0.0)
    assert res.idle_vehicle_seconds == 0.0
    assert res.estimated_fuel_liters == 0.0
    assert res.estimated_co2_kg == 0.0


def test_deterministic_emissions_calculation():
    """Verify emissions calculation matches documented mathematical model."""
    # 3600 vehicle-seconds of idling = 1.0 vehicle-hour
    # At 0.7 L/veh-hr -> 0.7 Liters
    # At 2.31 kg CO2/L -> 0.7 * 2.31 = 1.617 kg CO2
    res = calculate_emissions(idle_vehicle_seconds=3600.0)
    assert np.isclose(res.estimated_fuel_liters, 0.7, atol=1e-4)
    assert np.isclose(res.estimated_co2_kg, 1.617, atol=1e-4)


def test_custom_emissions_config():
    """Verify custom fuel rates and CO2 factors are applied."""
    cfg = EmissionsConfig(
        idle_fuel_rate_liters_per_hour=1.0,  # 1.0 L / hr
        co2_kg_per_liter=2.5,                # 2.5 kg / L
    )
    # 7200 vehicle-seconds = 2.0 vehicle-hours -> 2.0 Liters -> 5.0 kg CO2
    res = calculate_emissions(idle_vehicle_seconds=7200.0, config=cfg)
    assert np.isclose(res.estimated_fuel_liters, 2.0, atol=1e-4)
    assert np.isclose(res.estimated_co2_kg, 5.0, atol=1e-4)


def test_emissions_metrics_serialization():
    """Verify EmissionsMetrics serialization to dictionary."""
    res = calculate_emissions(idle_vehicle_seconds=1800.0)
    d = res.to_dict()
    assert "idle_vehicle_seconds" in d
    assert "estimated_fuel_liters" in d
    assert "estimated_co2_kg" in d
    assert d["idle_vehicle_seconds"] == 1800.0


# ---------------------------------------------------------------- engine: cross-street idling is counted
def test_engine_emissions_include_cross_street_idling_and_are_unchanged_without_it():
    import dataclasses

    from simulation.engine import TrafficSimulator
    from simulation.scenario import create_canonical_scenarios

    plan = {"I1": 45, "I2": 45, "I3": 45, "I4": 45}
    base = create_canonical_scenarios()["scenario_a_balanced"]

    # no cross traffic: emissions come from arterial waiting only (previous behaviour, unchanged)
    m0 = TrafficSimulator(base).simulate(plan, seed=3)
    assert m0.cross_street_waiting_time == 0.0
    assert m0.idle_vehicle_seconds == m0.normal_vehicles_waiting_time

    # with cross traffic: cross-street waiting is added, and the plan's starvation of cross streets shows up in CO2
    cross = dataclasses.replace(base, cross_street_rates={i: 0.4 for i in base.intersections})
    m1 = TrafficSimulator(cross).simulate(plan, seed=3)
    assert m1.cross_street_waiting_time > 0
    assert m1.idle_vehicle_seconds == pytest.approx(m1.normal_vehicles_waiting_time + m1.cross_street_waiting_time)
    assert m1.estimated_co2_kg == pytest.approx(m1.idle_vehicle_seconds * (0.7 / 3600.0) * 2.31, rel=1e-3)
    assert m1.estimated_co2_kg > m0.estimated_co2_kg  # more idling vehicles, more CO2
