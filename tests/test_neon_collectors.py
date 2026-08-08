from crtnm.drivers.neon.collectors.cpu import parse_cpu
from crtnm.drivers.neon.collectors.memory import parse_memory
from crtnm.drivers.neon.collectors.version import parse_version


def test_memory_parser():
    output = """
    memory utilization threshold        : 90%
    memory utilization thresholdrecover : 85%
    memory interval(second)             : 60

    MemTotal     MemFree         MemUsed

    1966940      790120          1176820

    memory utilization  : 59.84%
    """

    result = parse_memory(output)

    assert result["total_kb"] == 1966940
    assert result["free_kb"] == 790120
    assert result["used_kb"] == 1176820
    assert result["utilization_percent"] == 59.84
    assert result["threshold_percent"] == 90
    assert result["recover_threshold_percent"] == 85
    assert result["interval_seconds"] == 60


def test_cpu_parser():
    output = """
    CPU threshold trap enable: Enable
    Rising  threshold: 90
    Recovering  threshold: 80
    Trap transfer observation interval(second): 60

    Last 1 second CPU utilization:     63%
    Last 5 seconds CPU utilization:    30%
    Last 1 minute CPU utilization:     28%
    Last 5 minute CPU utilization:     28%
    Last 10 minutes CPU utilization:   27%
    Last 2 hours CPU utilization:      27%

    CPU    1SEC   5SEC   1MIN   5MIN   10MIN   2HOUR
    0      63%    31%    27%    28%    27%    27%
    1      63%    28%    28%    27%    27%    27%
    """

    result = parse_cpu(output)

    assert result["threshold_percent"] == 90
    assert result["recovering_threshold_percent"] == 80
    assert result["observation_interval_seconds"] == 60

    assert result["overall"]["one_second"] == 63
    assert result["overall"]["five_seconds"] == 30
    assert result["overall"]["one_minute"] == 28
    assert result["overall"]["five_minutes"] == 28
    assert result["overall"]["ten_minutes"] == 27
    assert result["overall"]["two_hours"] == 27

    assert len(result["processors"]) == 2

    assert result["processors"][0]["id"] == 0
    assert result["processors"][0]["one_second"] == 63

    assert result["processors"][1]["id"] == 1
    assert result["processors"][1]["five_seconds"] == 28


def test_version_parser():
    output = """
    Product Name: NEON8800-E-DC
    Product Version: P200R003C00
    Hardware Version: T.30
    PCB Version: A.1
    Software Version: 10.4.82_20260422(Compiled Apr 22 2026,10:45:18)
    NEON Version: 6.5.2_20260422
    Bootrom Version: 1.2.4
    CPLD Version: 1.1
    FPGA Version: RA2019:1.4_20211027
    FPGA2 Version: 1.1
    System MAC Address: 4CDF.3D1F.0D00
    Serial number: 140515022500A25908A0032G

    NEON8800-E-DC with
    2048M   bytes  DRAM
    32  M   bytes  Flash Memory
    4096M   bytes  eMMC

    System uptime is 35 days, 1 hours, 56 minutes
    """

    result = parse_version(output)

    assert result["product_name"] == "NEON8800-E-DC"
    assert result["product_version"] == "P200R003C00"
    assert result["hardware_version"] == "T.30"
    assert result["software_version"].startswith(
        "10.4.82_20260422"
    )
    assert result["neon_version"] == "6.5.2_20260422"
    assert result["system_mac"] == "4CDF.3D1F.0D00"
    assert result["serial_number"] == (
        "140515022500A25908A0032G"
    )

    assert result["memory"]["dram"] == "2048M"
    assert result["memory"]["flash"] == "32M"
    assert result["memory"]["emmc"] == "4096M"

    assert result["uptime"] == (
        "35 days, 1 hours, 56 minutes"
    )