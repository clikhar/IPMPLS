"""Explicit driver registration and vendor lookup."""
from crtnm.drivers.contracts import NetworkDriver
from crtnm.drivers.exceptions import DriverError


class DriverRegistry:
    """Registry prevents vendor-specific logic leaking into use cases."""

    def __init__(self) -> None:
        self._drivers: dict[str, NetworkDriver] = {}

    def register(self, driver: NetworkDriver) -> None:
        """Register one driver per normalized vendor name."""
        name = driver.vendor.lower()
        if name in self._drivers:
            raise ValueError(f"Driver already registered for vendor: {name}")
        self._drivers[name] = driver

    def resolve(self, vendor: str) -> NetworkDriver:
        """Return the driver for a vendor, or a clear safe error."""
        try:
            return self._drivers[vendor.lower()]
        except KeyError as error:
            raise DriverError(f"No driver is installed for vendor '{vendor}'") from error

    def has(self, vendor: str) -> bool:
        """Return whether a normalized vendor has been registered."""
        return vendor.lower() in self._drivers
