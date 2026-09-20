"""Emissions, Fuel Consumption, and Environmental Impact Model for QuantumFlow.

Provides deterministic calculations for vehicle idling delays, fuel consumption,
and carbon emissions derived from microscopic simulation states.

Mathematical Model:
- Standard Passenger Car Idling Fuel Burn Rate:
    r_fuel = 0.7 Liters / vehicle-hour = 0.7 / 3600 Liters / vehicle-second (~0.0001944 L/veh-s)
- Direct CO2 Conversion Factor (Gasoline combustion standard):
    c_co2 = 2.31 kg CO2 / Liter of fuel burned

Total Fuel Burn (idle_vehicle_seconds = arterial + cross-street civilian waiting time):
    Fuel(L) = idle_vehicle_seconds * (r_fuel_per_hour / 3600.0)

Total Carbon Output:
    CO2(kg) = Fuel(L) * c_co2
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional


@dataclass(frozen=True)
class EmissionsConfig:
    """Configurable parameters for the environmental impact model.

    Attributes:
        idle_fuel_rate_liters_per_hour: Idling fuel consumption rate (L/veh-hr).
        co2_kg_per_liter: EPA standard carbon emission factor per liter of fuel (kg CO2 / L).
    """

    idle_fuel_rate_liters_per_hour: float = 0.7
    co2_kg_per_liter: float = 2.31


@dataclass(frozen=True)
class EmissionsMetrics:
    """Calculated environmental impact metrics.

    Attributes:
        idle_vehicle_seconds: Total cumulative seconds spent idling stationary in queues.
        estimated_fuel_liters: Total estimated fuel consumed during idling.
        estimated_co2_kg: Total estimated carbon dioxide emissions produced.
    """

    idle_vehicle_seconds: float
    estimated_fuel_liters: float
    estimated_co2_kg: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def calculate_emissions(
    idle_vehicle_seconds: float,
    config: Optional[EmissionsConfig] = None,
) -> EmissionsMetrics:
    """Calculate fuel consumption and carbon emissions from cumulative vehicle idling delay.

    Args:
        idle_vehicle_seconds: Total stationary vehicle seconds in the network.
        config: Optional custom EmissionsConfig.

    Returns:
        EmissionsMetrics container with fuel and CO2 amounts.
    """
    cfg = config if config is not None else EmissionsConfig()
    idle_s = max(0.0, float(idle_vehicle_seconds))
    fuel_l = round(idle_s * (cfg.idle_fuel_rate_liters_per_hour / 3600.0), 4)
    co2_kg = round(fuel_l * cfg.co2_kg_per_liter, 4)

    return EmissionsMetrics(
        idle_vehicle_seconds=idle_s,
        estimated_fuel_liters=fuel_l,
        estimated_co2_kg=co2_kg,
    )
