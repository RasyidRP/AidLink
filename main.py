import networkx as nx
import osmnx as ox
import geopandas as gpd
import folium
from shapely.geometry import Point
import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate('/Users/aladlyy/Downloads/aidlink17-firebase-adminsdk-l9ndl-b190973eb9.json')
firebase_admin.initialize_app(cred)

db = firestore.client()

ox.config(log_console=True, use_cache=True)
place_name = "South Jakarta, Indonesia"  # Can be made as an input
G = ox.graph_from_place(place_name, network_type='drive')
center_lat, center_lon = ox.geocode(place_name)

my_position = -6.240141355259069, 106.79019842321343  # Can be made as an input

hospitals = None
police_stations = None
food_banks = None

try:
    hospitals = ox.geometries_from_place(place_name, tags={'amenity': 'hospital', 'emergency': True})
    police_stations = ox.geometries_from_place(place_name, tags={'amenity': 'police'})
    food_banks = ox.geometries_from_place(place_name, tags={'amenity': 'food_bank'})
except Exception as e:
    print(f"Error retrieving amenities: {e}")

m = folium.Map(location=[center_lat, center_lon], zoom_start=12)

for u, v, key, data in G.edges(keys=True, data=True):
    x = [G.nodes[u]['y'], G.nodes[v]['y']]
    y = [G.nodes[u]['x'], G.nodes[v]['x']]
    folium.PolyLine(locations=list(zip(x, y)), color='blue', weight=2).add_to(m)


def add_markers(df, color, icon, label):
    if df is not None and not df.empty:
        for idx, row in df.iterrows():
            name = row['name'] if 'name' in row else f'Unnamed {label}'
            lat, lon = row.geometry.centroid.y, row.geometry.centroid.x
            folium.Marker(
                location=[lat, lon],
                popup=name,
                icon=folium.Icon(color=color, icon=icon)
            ).add_to(m)
    else:
        print(f'No {label} Found.')


add_markers(hospitals, 'red', 'plus-sign', 'Hospital')
add_markers(police_stations, 'blue', 'flag', 'Police Station')
add_markers(food_banks, 'orange', 'cutlery', 'Food Banks')

folium.Marker(
    location=[my_position[0], my_position[1]],
    popup='My Position',
    icon=folium.Icon(color='purple', icon='user')
).add_to(m)


def amenities_finder(amenity_type, user_position, G, m, amenities):
    if amenities is not None and not amenities.empty:
        user_point = Point(user_position[1], user_position[0])
        amenities['distance'] = amenities.geometry.apply(lambda geom: user_point.distance(geom.centroid))

        nearest_idx = amenities['distance'].idxmin()
        nearest_amenity = amenities.loc[nearest_idx]

        orig_node = ox.distance.nearest_nodes(G, user_position[1], user_position[0])

        amenity_lat, amenity_lon = nearest_amenity.geometry.centroid.y, nearest_amenity.geometry.centroid.x
        amenity_node = ox.distance.nearest_nodes(G, amenity_lon, amenity_lat)

        shortest_path = nx.shortest_path(G, orig_node, amenity_node, weight='length')

        route_points = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in shortest_path]
        folium.PolyLine(route_points, color='red', weight=5, opacity=0.7).add_to(m)

        folium.Marker(
            location=[amenity_lat, amenity_lon],
            popup=nearest_amenity['name'] if 'name' in nearest_amenity else f'Unnamed {amenity_type.captalize()}',
            icon=folium.Icon(color='beige', icon='info-sign')
        ).add_to(m)
    else:
        print(f"No {amenity_type}s found!")


def add_shelter(name, lat, lon):
    shelter_data = {
        'name': name,
        'latitude': lat,
        'longitude': lon
    }
    db.collection('shelters').add(shelter_data)
    print(f"Shelter '{name}' added at {lat}, {lon}.")


def get_shelter():
    shelters_ref = db.collection('shelters')
    shelters = shelters_ref.stream()

    for shelter in shelters:
        data = shelter.to_dict()

        if 'latitude' in data and 'longitude' in data:
            lat = float(data['latitude'])
            lon = float(data['longitude'])
            name = data.get('name', 'Unnamed Shelter')

            folium.Marker(
                location=[lat, lon],
                popup=name,
                icon=folium.Icon(color='lightgreen', icon='home')
            ).add_to(m)
        else:
            print(f"Skipped shelter due to missing location data: {data}")


# Input
amenity_type = input("Search (police/hospital): ")
if amenity_type == 'police':
    amenities_finder(amenity_type, my_position, G, m, police_stations)
elif amenity_type == 'hospital':
    amenities_finder(amenity_type, my_position, G, m, hospitals)

add_shelter_name = input("Add New Shelter Name: ")
add_shelter_lat = input("Add New Shelter Latitude: ")
add_shelter_lon = input("Add New Shelter Longitude: ")
add_shelter(add_shelter_name, add_shelter_lat, add_shelter_lon)

get_shelter()
m.save("map.html")
