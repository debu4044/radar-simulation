from radar_simulator import read_radar_coordinates

lat, lon = read_radar_coordinates(
    "radar.kml"
)

print("Radar Coordinates")
print("-----------------")
print("Latitude :", lat)
print("Longitude:", lon)