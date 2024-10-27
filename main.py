import osmnx as ox
import folium
import networkx as nx
from flask import Flask, render_template, request, jsonify
from shapely.geometry import Point
import firebase_admin
from firebase_admin import credentials, firestore, auth
import pandas as pd

# Initialize Firebase
cred = credentials.Certificate('/Users/aladlyy/Downloads/aidlink17-firebase-adminsdk-l9ndl-b190973eb9.json')
firebase_admin.initialize_app(cred)
db = firestore.client()
email = ""

def get_loc(collection_names, icon_color, icon_type, m):
    collection_ref = db.collection(collection_names)
    documents = collection_ref.stream()

    for doc in documents:
        data = doc.to_dict()

        if 'latitude' in data and 'longitude' in data:
            lat = float(data['latitude'])
            lon = float(data['longitude'])
            name = data.get('name', f'Unnamed {collection_names.capitalize()}')

            folium.Marker(
                location=[lat, lon],
                popup=name,
                icon=folium.Icon(color=icon_color, icon=icon_type)
            ).add_to(m)
        else:
            print(f"Skipped shelter due to missing location data: {data}")


def amenities_finder(amenity_type, user_position, G, m, amenities):
    if amenities is not None and not amenities.empty:
        user_point = Point(user_position[1], user_position[0])
        amenities['distance'] = amenities.geometry.apply(lambda geom: user_point.distance(geom.centroid))

        nearest_idx = amenities['distance'].idxmin()
        nearest_amenity = amenities.loc[nearest_idx]

        orig_node = ox.distance.nearest_nodes(G, float(user_position[1]), float(user_position[0]))
        amenity_lat, amenity_lon = nearest_amenity.geometry.centroid.y, nearest_amenity.geometry.centroid.x
        amenity_node = ox.distance.nearest_nodes(G, amenity_lon, amenity_lat)

        shortest_path = nx.shortest_path(G, orig_node, amenity_node, weight='length')
        route_points = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in shortest_path]
        folium.PolyLine(route_points, color='red', weight=5, opacity=1).add_to(m)

        buffer = 0.002  # Adjust this value for more or less zoom
        bounds = [[min([point[0] for point in route_points]) - buffer,
                   min([point[1] for point in route_points]) - buffer],
                  [max([point[0] for point in route_points]) + buffer,
                   max([point[1] for point in route_points]) + buffer]]
        m.fit_bounds(bounds)

        folium.Marker(
            location=[amenity_lat, amenity_lon],
            popup=nearest_amenity['name'] if 'name' in nearest_amenity else f'Unnamed {amenity_type.capitalize()}',
            icon=folium.Icon(color='beige', icon='info-sign')
        ).add_to(m)


def add_amenity(amenity_type, name, lat, lon):
    amenity_data = {
        'name': name,
        'latitude': lat,
        'longitude': lon
    }
    db.collection(amenity_type).add(amenity_data)


def add_roadblocks(desc, lat, lon):
    roadblocks_data = {
        'desc': desc,
        'latitude': lat,
        'longitude': lon
    }
    db.collection('roadblocks').add(roadblocks_data)


def remove_roadblocks_from_graph(graph, roadblocks):
    for roadblock in roadblocks:
        lat, lon = roadblock['latitude'], roadblock['longitude']
        nearest_node = ox.distance.nearest_nodes(graph, lon, lat)

        # Remove the node or edges connected to this roadblock
        if nearest_node in graph:
            graph.remove_node(nearest_node)  # Removes the node itself and connected edges


def get_all_roadblocks():
    roadblocks = []
    # Retrieve all roadblock data from the database
    docs = db.collection('roadblocks').stream()
    for doc in docs:
        roadblocks.append(doc.to_dict())  # Convert each roadblock to a dictionary with 'latitude', 'longitude', etc.
    return roadblocks


def nearest_amenity_finder(amenity_type, my_position, G, m):
    amenities_ref = db.collection(amenity_type)
    amenities = amenities_ref.stream()

    amenity_locations = []
    for amenity in amenities:
        data = amenity.to_dict()
        if 'latitude' in data and 'longitude' in data:
            lat = float(data['latitude'])
            lon = float(data['longitude'])
            name = data.get('name', f'Unnamed {amenity_type.capitalize()}')
            amenity_locations.append((name, lat, lon))

            folium.Marker(
                location=[lat, lon],
                popup=name,
                icon=folium.Icon(color='lightgreen' if amenity_type == 'shelters' else 'purple', icon='info-sign')
            ).add_to(m)

    # Debugging output
    print(f"Found {len(amenity_locations)} {amenity_type} amenities.")
    for loc in amenity_locations:
        print(f"Amenity: {loc[0]}, Latitude: {loc[1]}, Longitude: {loc[2]}")

    if not amenity_locations:
        return

    user_point = Point(my_position[1], my_position[0])
    nearest_amenity = min(
        amenity_locations,
        key=lambda loc: user_point.distance(Point(loc[2], loc[1]))  # Calculate distance
    )

    amenity_name, amenity_lat, amenity_lon = nearest_amenity
    orig_node = ox.distance.nearest_nodes(G, my_position[1], my_position[0])
    amenity_node = ox.distance.nearest_nodes(G, amenity_lon, amenity_lat)

    print(f"User Node: {orig_node}, Nearest Amenity Node: {amenity_node}")

    roadblocks = get_all_roadblocks()
    remove_roadblocks_from_graph(G, roadblocks)

    shortest_path = nx.shortest_path(G, orig_node, amenity_node, weight='length')
    route_points = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in shortest_path]

    print(f"Route Points: {route_points}")

    folium.PolyLine(route_points, color='red', weight=5, opacity=1).add_to(m)

    buffer = 0.002  # Adjust this value for more or less zoom
    bounds = [[min([point[0] for point in route_points]) - buffer,
               min([point[1] for point in route_points]) - buffer],
              [max([point[0] for point in route_points]) + buffer,
               max([point[1] for point in route_points]) + buffer]]

    m.fit_bounds(bounds)

    folium.Marker(
        location=[amenity_lat, amenity_lon],
        popup=f"Nearest {amenity_type.capitalize()}: {amenity_name}",
        icon=folium.Icon(color='red', icon='info-sign')
    ).add_to(m)


app = Flask(__name__)

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    first_name = data.get('firstName')
    last_name = data.get('lastName')

    try:
        # Create a new user
        user = auth.create_user(
            email=email,
            password=password
        )
        return jsonify({
            'message': 'Account created successfully',
            'uid': user.uid,
            'firstName': first_name,
            'lastName': last_name
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    try:
        # Use Firebase's verify_id_token to authenticate users
        # Note: You usually need to do this with a client-side SDK and not directly with the password.
        # However, we can send a custom token for this demo.
        user = auth.get_user_by_email(email)
        token = auth.create_custom_token(user.uid)
        return jsonify({
            'message': 'Login successful',
            'token': token.decode('utf-8')  # This token can be used on client-side for further auth
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/survivors', methods=['GET', 'POST'])
def survivors():
    user_action = request.form.get('action_type')

    if user_action == 'add_roadblock':
        return render_template('add_roadblock.html')
    elif user_action == 'find_amenity':
        return render_template('find_amenity.html')
    else:
        return render_template('.html', map_html=None)


@app.route('/add_roadblock', methods=['GET', 'POST'])
def add_roadblock():
    map_html = None

    if request.method == 'POST':
        place_name = request.form.get('place_name', "South Jakarta, Indonesia")
        desc = request.form.get('desc')
        lat = float(request.form.get('lat'))
        lon = float(request.form.get('lon'))

        ox.config(log_console=True, use_cache=True)
        G = ox.graph_from_place(place_name, network_type='drive')

        hospitals = ox.geometries_from_place(place_name, tags={'amenity': 'hospital', 'emergency': True})
        police_stations = ox.geometries_from_place(place_name, tags={'amenity': 'police'})

        m = folium.Map(location=[lat, lon], zoom_start=15)

        for u, v, key, data in G.edges(keys=True, data=True):
            x = [G.nodes[u]['y'], G.nodes[v]['y']]
            y = [G.nodes[u]['x'], G.nodes[v]['x']]
            folium.PolyLine(locations=list(zip(x, y)), color='blue', weight=2).add_to(m)

        # Add markers for existing amenities
        add_markers(hospitals, 'red', 'plus-sign', 'Hospital', m)
        add_markers(police_stations, 'blue', 'flag', 'Police Station', m)

        add_roadblocks(desc, lat, lon)

        get_loc('roadblocks', 'darkpurple', 'minus-sign', m)
        get_loc('shelters', 'lightgreen', 'home', m)
        get_loc('foodbanks', 'orange', 'cutlery', m)

        map_path = "templates/map.html"
        m.save(map_path)

        with open(map_path, "r") as file:
            map_html = file.read()

    return render_template('add_roadblock.html', map_html=map_html)

@app.route('/home')
def home():
    return render_template('home.html')


@app.route('/logout')
def logout():
    return render_template('index.html')

@app.route('/about')
def aboutt():
    return render_template('about.html')

@app.route('/contact')
def meetourpage():
    return render_template('meetourpage.html')

@app.route('/survivorpage')
def survivorspage():
    return render_template('survivor-portal.html')

@app.route('/providerpage')
def providers():
    return render_template('provider-portal.html')

@app.route('/find_amenity', methods=['GET', 'POST'])
def find_amenity():
    if request.method == 'POST':
        place_name = request.form.get('place_name', 'South Jakarta, Indonesia')
        lat = float(request.form['lat'])
        lon = float(request.form['lon'])
        my_position = [lat, lon]

        # Initialize OSMnx
        ox.config(log_console=True, use_cache=True)
        G = ox.graph_from_place(place_name, network_type='drive')

        hospitals = ox.geometries_from_place(place_name, tags={'amenity': 'hospital', 'emergency': True})
        police_stations = ox.geometries_from_place(place_name, tags={'amenity': 'police'})

        # Create map
        m = folium.Map(location=[float(my_position[0]), float(my_position[1])], zoom_start=15)

        # Plot network edges
        for u, v, key, data in G.edges(keys=True, data=True):
            x = [G.nodes[u]['y'], G.nodes[v]['y']]
            y = [G.nodes[u]['x'], G.nodes[v]['x']]
            folium.PolyLine(locations=list(zip(x, y)), color='blue', weight=2).add_to(m)

        # Add markers for existing amenities
        add_markers(hospitals, 'red', 'plus-sign', 'Hospital', m)
        add_markers(police_stations, 'blue', 'flag', 'Police Station', m)

        # Add user position marker
        folium.Marker(
            location=[lat, lon],
            popup='My Position',
            icon=folium.Icon(color='purple', icon='user')
        ).add_to(m)

        # Handle amenity finding
        amenity_type = request.form.get('amenity_type')
        user_position = (float(my_position[0]), float(my_position[1]))  # Convert to float for calculations
        if amenity_type == 'shelters':
            nearest_amenity_finder(amenity_type, my_position, G, m)
            get_loc('shelters', 'lightgreen', 'home', m)
            get_loc('foodbanks', 'orange', 'cutlery', m)
            get_loc('roadblocks', 'darkpurple', 'minus-sign', m)
        elif amenity_type == 'foodbanks':
            nearest_amenity_finder(amenity_type, my_position, G, m)
            get_loc('foodbanks', 'orange', 'cutlery', m)
            get_loc('shelters', 'lightgreen', 'home', m)
            get_loc('roadblocks', 'darkpurple', 'minus-sign', m)
        if amenity_type in ['police', 'hospital']:
            amenities_finder(amenity_type, user_position, G, m,
                             police_stations if amenity_type == 'police' else hospitals)
            get_loc('foodbanks', 'orange', 'cutlery', m)
            get_loc('shelters', 'lightgreen', 'home', m)
            get_loc('roadblocks', 'darkpurple', 'minus-sign', m)

        map_path = "templates/map.html"
        m.save(map_path)

        with open(map_path, "r") as file:
            map_html = file.read()

    return render_template('find_amenity.html', map_html=map_html)


@app.route('/aid_providers', methods=['GET', 'POST'])
def aid_providers():
    if request.method == 'POST':
        place_name = request.form.get('place_name', "South Jakarta, Indonesia")
        amenity_type = request.form['amenity_type']
        name = request.form['name']
        lat = float(request.form['lat'])
        lon = float(request.form['lon'])

        my_position = request.form.get('my_position', "-6.235708540830825,106.8033227557353").split(',')
        my_position = [float(coord) for coord in my_position]

        ox.config(log_console=True, use_cache=True)
        G = ox.graph_from_place(place_name, network_type='drive')

        hospitals = ox.geometries_from_place(place_name, tags={'amenity': 'hospital', 'emergency': True})
        police_stations = ox.geometries_from_place(place_name, tags={'amenity': 'police'})

        add_amenity(amenity_type, name, lat, lon)

        m = folium.Map(location=[float(my_position[0]), float(my_position[1])], zoom_start=15)

        for u, v, key, data in G.edges(keys=True, data=True):
            x = [G.nodes[u]['y'], G.nodes[v]['y']]
            y = [G.nodes[u]['x'], G.nodes[v]['x']]
            folium.PolyLine(locations=list(zip(x, y)), color='blue', weight=2).add_to(m)

        # Add markers for existing amenities
        add_markers(hospitals, 'red', 'plus-sign', 'Hospital', m)
        add_markers(police_stations, 'blue', 'flag', 'Police Station', m)

        get_loc('shelters', 'lightgreen', 'home', m)
        get_loc('foodbanks', 'orange', 'cutlery', m)
        get_loc('roadblocks', 'darkpurple', 'minus-sign', m)

        map_path = "templates/map.html"
        m.save(map_path)

        with open(map_path, "r") as file:
            map_html = file.read()

    return render_template('aid_providers.html', map_html=map_html)


@app.route('/', methods=['GET', 'POST'])
def index():
    map_html = None  # Initialize map_html to None
    if request.method == 'POST':
        place_name = request.form.get('place_name', "South Jakarta, Indonesia")
        my_position = request.form.get('my_position', "-6.235708540830825,106.8033227557353").split(',')
        my_position = [float(coord) for coord in my_position]

        # Initialize OSMnx
        ox.config(log_console=True, use_cache=True)
        G = ox.graph_from_place(place_name, network_type='drive')

        hospitals = ox.geometries_from_place(place_name, tags={'amenity': 'hospital', 'emergency': True})
        police_stations = ox.geometries_from_place(place_name, tags={'amenity': 'police'})

        # Create map
        m = folium.Map(location=[float(my_position[0]), float(my_position[1])], zoom_start=15)

        # Plot network edges
        for u, v, key, data in G.edges(keys=True, data=True):
            x = [G.nodes[u]['y'], G.nodes[v]['y']]
            y = [G.nodes[u]['x'], G.nodes[v]['x']]
            folium.PolyLine(locations=list(zip(x, y)), color='blue', weight=2).add_to(m)

        # Add markers for existing amenities
        add_markers(hospitals, 'red', 'plus-sign', 'Hospital', m)
        add_markers(police_stations, 'blue', 'flag', 'Police Station', m)

        # Add user position marker
        folium.Marker(
            location=[float(my_position[0]), float(my_position[1])],
            popup='My Position',
            icon=folium.Icon(color='purple', icon='user')
        ).add_to(m)

        # Handle amenity finding
        amenity_type = request.form.get('amenity_type')
        user_position = (float(my_position[0]), float(my_position[1]))  # Convert to float for calculations
        if amenity_type == 'shelters':
            nearest_amenity_finder(amenity_type, my_position, G, m)
            get_loc('shelters', 'lightgreen', 'home', m)
            get_loc('foodbanks', 'orange', 'cutlery', m)
            get_loc('roadblocks', 'darkpurple', 'minus-sign', m)
        elif amenity_type == 'foodbanks':
            nearest_amenity_finder(amenity_type, my_position, G, m)
            get_loc('foodbanks', 'orange', 'cutlery', m)
            get_loc('shelters', 'lightgreen', 'home', m)
            get_loc('roadblocks', 'darkpurple', 'minus-sign', m)

        if amenity_type in ['police', 'hospital']:
            amenities_finder(amenity_type, user_position, G, m,
                             police_stations if amenity_type == 'police' else hospitals)
            get_loc('foodbanks', 'orange', 'cutlery', m)
            get_loc('shelters', 'lightgreen', 'home', m)
            get_loc('roadblocks', 'darkpurple', 'minus-sign', m)

        map_path = "templates/map.html"
        m.save(map_path)

        with open(map_path, "r") as file:
            map_html = file.read()

    return render_template('index.html', map_html=map_html)


def add_markers(df, color, icon, label, m):
    if df is not None and not df.empty:
        for idx, row in df.iterrows():
            name = row['name'] if 'name' in row else f'Unnamed {label}'
            lat, lon = row.geometry.centroid.y, row.geometry.centroid.x
            folium.Marker(
                location=[lat, lon],
                popup=name,
                icon=folium.Icon(color=color, icon=icon)
            ).add_to(m)


if __name__ == '__main__':
    app.run(debug=True)
