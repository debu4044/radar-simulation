import csv
import json
import math
import random
import socket
import time
import xml.etree.ElementTree as ET

from datetime import datetime
from geopy.distance import geodesic


# ==========================================================
# CONFIGURATION
# ==========================================================

# KML containing a SINGLE radar point
KML_FILE = "radar.kml"

GENERATE_KML_OUTPUT = True
KML_OUTPUT_FILE = "generated_alerts.kml"

# Coverage Zone (meters)
MIN_RANGE_M = 50
MAX_RANGE_M = 5000

# Number of alerts
NUM_ALERTS = 10

# Priority Thresholds
HIGH_PRIORITY_MAX = 1500
MEDIUM_PRIORITY_MAX = 3500

# Timing between alerts
MIN_DELAY_SEC = 2
MAX_DELAY_SEC = 5

# UDP Settings
UDP_IP = "127.0.0.1"
UDP_PORT = 5005

# Packet Format
# Options:
# "json"
# "spider"
UDP_FORMAT = "json"

# CSV Output
CSV_OUTPUT_FILE = "generated_alerts.csv"

# ==========================================================
# SPIDER CONFIGURATION
# ==========================================================

DEVICE_ID = 3
DEVICE_TYPE = 9

DEVICE_HEIGHT = 0
DEVICE_BEARING = 0

FOV_START = 0
FOV_END = 360

DEFAULT_TARGET_TYPE = 0
DEFAULT_CONFIDENCE = 95
DEFAULT_SPEED = 0
DEFAULT_ELEVATION = 0
DEFAULT_HEIGHT = 0

# ==========================================================
# KML PARSER
# ==========================================================


def read_radar_coordinates(kml_file):
    """
    Reads radar coordinates from a KML containing
    a single Point.
    Returns:
        latitude, longitude
    """

    tree = ET.parse(kml_file)
    root = tree.getroot()

    namespace = {
        "kml": "http://www.opengis.net/kml/2.2"
    }

    coord_element = root.find(
        ".//kml:Point/kml:coordinates",
        namespace
    )

    if coord_element is None:
        raise Exception(
            "No Point coordinates found in KML."
        )

    coords = coord_element.text.strip()

    values = coords.split(",")

    if len(values) < 2:
        raise Exception(
            "Invalid coordinate format in KML."
        )

    longitude = float(values[0])
    latitude = float(values[1])

    return latitude, longitude


# ==========================================================
# ALERT GENERATION
# ==========================================================

def generate_uniform_distance():
    """
    Generates a distance uniformly distributed
    over the area of the annulus.

    NOT simply random.uniform(min,max).
    """

    return math.sqrt(
        random.uniform(
            MIN_RANGE_M ** 2,
            MAX_RANGE_M ** 2
        )
    )


def determine_priority(distance):

    if distance <= HIGH_PRIORITY_MAX:
        return "HIGH"

    if distance <= MEDIUM_PRIORITY_MAX:
        return "MEDIUM"

    return "LOW"


def generate_alert_location(
    radar_lat,
    radar_lon
):
    """
    Generates random point inside
    the coverage annulus.
    """

    bearing = random.uniform(0, 360)

    distance = generate_uniform_distance()

    destination = geodesic(
        meters=distance
    ).destination(
        (radar_lat, radar_lon),
        bearing
    )

    return (
        destination.latitude,
        destination.longitude,
        distance,
        bearing
    )


# ==========================================================
# PACKET BUILDERS
# ==========================================================

def build_json_packet(alert):

    return json.dumps(alert)


def build_spider_packet(
    alert,
    radar_lat,
    radar_lon
):
    """
    SPIDER radar packet format
    """

    event_time = int(time.time())

    packet = [
        DEVICE_ID,
        DEVICE_TYPE,
        radar_lat,
        radar_lon,
        DEVICE_HEIGHT,
        DEVICE_BEARING,
        FOV_START,
        FOV_END,
        alert["alert_id"],
        alert["latitude"],
        alert["longitude"],
        round(alert["distance_m"], 2),
        round(alert["bearing"], 2),
        DEFAULT_TARGET_TYPE,
        DEFAULT_CONFIDENCE,
        event_time,
        0,
        "",
        DEFAULT_SPEED,
        DEFAULT_ELEVATION,
        DEFAULT_HEIGHT
    ]

    return ",".join(map(str, packet))


# ==========================================================
# UDP
# ==========================================================

udp_socket = socket.socket(
    socket.AF_INET,
    socket.SOCK_DGRAM
)


def send_udp(packet):

    udp_socket.sendto(
        packet.encode("utf-8"),
        (UDP_IP, UDP_PORT)
    )


# ==========================================================
# KML OUTPUT
# ==========================================================
def generate_output_kml(
    radar_lat,
    radar_lon,
    alerts,
    output_file
):

    circle_points_outer = []
    circle_points_inner = []

    for angle in range(361):

        outer_point = geodesic(
            meters=MAX_RANGE_M
        ).destination(
            (radar_lat, radar_lon),
            angle
        )

        circle_points_outer.append(
            f"{outer_point.longitude},{outer_point.latitude},0"
        )

        inner_point = geodesic(
            meters=MIN_RANGE_M
        ).destination(
            (radar_lat, radar_lon),
            angle
        )

        circle_points_inner.append(
            f"{inner_point.longitude},{inner_point.latitude},0"
        )

    kml_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>

    <name>Radar Simulation Output</name>

    <Style id="radarStyle">
        <IconStyle>
            <color>ff0000ff</color>
            <scale>1.4</scale>
        </IconStyle>
    </Style>

    <Style id="highStyle">
        <IconStyle>
            <color>ff0000ff</color>
            <scale>1.2</scale>
        </IconStyle>
    </Style>

    <Style id="mediumStyle">
        <IconStyle>
            <color>ff00ffff</color>
            <scale>1.2</scale>
        </IconStyle>
    </Style>

    <Style id="lowStyle">
        <IconStyle>
            <color>ff00ff00</color>
            <scale>1.2</scale>
        </IconStyle>
    </Style>

    <Placemark>
        <name>Radar</name>
        <styleUrl>#radarStyle</styleUrl>
        <Point>
            <coordinates>
                {radar_lon},{radar_lat},0
            </coordinates>
        </Point>
    </Placemark>

    <Placemark>
        <name>Coverage Boundary ({MAX_RANGE_M}m)</name>
        <LineString>
            <coordinates>
                {" ".join(circle_points_outer)}
            </coordinates>
        </LineString>
    </Placemark>

    <Placemark>
        <name>Exclusion Zone ({MIN_RANGE_M}m)</name>
        <LineString>
            <coordinates>
                {" ".join(circle_points_inner)}
            </coordinates>
        </LineString>
    </Placemark>
'''

    for alert in alerts:

        if alert["priority"] == "HIGH":
            style = "#highStyle"

        elif alert["priority"] == "MEDIUM":
            style = "#mediumStyle"

        else:
            style = "#lowStyle"

        kml_content += f'''
    <Placemark>
        <name>Alert {alert["alert_id"]}</name>
        <description>
Priority: {alert["priority"]}
Distance: {alert["distance_m"]}m
Timestamp: {alert["timestamp"]}
        </description>

        <styleUrl>{style}</styleUrl>

        <Point>
            <coordinates>
                {alert["longitude"]},
                {alert["latitude"]},
                0
            </coordinates>
        </Point>
    </Placemark>
'''

    kml_content += """
</Document>
</kml>
"""

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as f:
        f.write(kml_content)
# MAIN SIMULATION
# ==========================================================

def run_simulation():

    radar_lat, radar_lon = read_radar_coordinates(
        KML_FILE
    )

    print("\n===================================")
    print("RADAR ALERT SIMULATOR")
    print("===================================")
    print(f"Radar Lat : {radar_lat}")
    print(f"Radar Lon : {radar_lon}")
    print(f"Format    : {UDP_FORMAT}")
    print("===================================\n")

    csv_alerts = []

    for alert_id in range(
        1,
        NUM_ALERTS + 1
    ):

        (
            alert_lat,
            alert_lon,
            distance,
            bearing
        ) = generate_alert_location(
            radar_lat,
            radar_lon
        )

        priority = determine_priority(
            distance
        )

        timestamp = datetime.utcnow().isoformat()

        alert = {
            "alert_id": alert_id,
            "priority": priority,
            "latitude": round(alert_lat, 8),
            "longitude": round(alert_lon, 8),
            "distance_m": round(distance, 2),
            "bearing": round(bearing, 2),
            "timestamp": timestamp
        }

        if UDP_FORMAT.lower() == "json":

            packet = build_json_packet(
                alert
            )

        elif UDP_FORMAT.lower() == "spider":

            packet = build_spider_packet(
                alert,
                radar_lat,
                radar_lon
            )

        else:

            raise ValueError(
                f"Unsupported UDP_FORMAT: {UDP_FORMAT}"
            )

        send_udp(packet)

        csv_alerts.append(alert)

        print(
            f"[{alert_id}/{NUM_ALERTS}] "
            f"{priority:<6} "
            f"{distance:8.2f}m "
            f"({alert_lat:.6f}, {alert_lon:.6f})"
        )

        if alert_id < NUM_ALERTS:

            delay = random.uniform(
                MIN_DELAY_SEC,
                MAX_DELAY_SEC
            )

            print(
                f"Waiting {delay:.2f} seconds...\n"
            )

            time.sleep(delay)

    # ======================================================
    # CSV EXPORT
    # ======================================================

    with open(
        CSV_OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        writer.writerow([
            "alert_id",
            "priority",
            "latitude",
            "longitude",
            "distance_m",
            "bearing",
            "timestamp"
        ])

        for alert in csv_alerts:

            writer.writerow([
                alert["alert_id"],
                alert["priority"],
                alert["latitude"],
                alert["longitude"],
                alert["distance_m"],
                alert["bearing"],
                alert["timestamp"]
            ])

    print("\n===================================")

    if GENERATE_KML_OUTPUT:

        generate_output_kml(
            radar_lat,
            radar_lon,
            csv_alerts,
            KML_OUTPUT_FILE
        )

        print(
            f"KML Saved: {KML_OUTPUT_FILE}"
        )
    print("\n===================================")
    print("SIMULATION COMPLETE")
    print(f"CSV Saved: {CSV_OUTPUT_FILE}")

    if GENERATE_KML_OUTPUT:
        print(f"KML Saved: {KML_OUTPUT_FILE}")

    print("===================================")


if __name__ == "__main__":
    run_simulation()