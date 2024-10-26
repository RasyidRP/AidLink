// Replace with your Mapbox Access Token
mapboxgl.accessToken = 'pk.eyJ1IjoiZ3JleWhhbWUiLCJhIjoiY20ycWJmZzJtMG9yYjJtb2dpN2xlbzlldyJ9.IGL3pSJx_3_l8jNzycduIg';

// Create the map instance
const map = new mapboxgl.Map({
    container: 'map', // Container ID
    style: 'mapbox://styles/mapbox/streets-v11', // Map style
    center: [-74.5, 40], // Initial center [lng, lat]
    zoom: 9 // Initial zoom level
});

// Add navigation controls (zoom, compass)
map.addControl(new mapboxgl.NavigationControl());

// Example resource data
const resources = [
    {
        type: 'Food',
        coordinates: [-74.5, 40.7],
        description: 'Food Distribution Center - 100 meals available'
    },
    {
        type: 'Water',
        coordinates: [-74.6, 40.8],
        description: 'Water Supply - 200 liters available'
    },
    {
        type: 'Shelter',
        coordinates: [-74.4, 40.6],
        description: 'Emergency Shelter - Capacity 50 people'
    }
];

// Function to add markers to the map
resources.forEach(resource => {
    const marker = new mapboxgl.Marker({ color: resource.type === 'Food' ? 'orange' : (resource.type === 'Water' ? 'blue' : 'green') })
        .setLngLat(resource.coordinates)
        .setPopup(new mapboxgl.Popup().setHTML(`<h3>${resource.type}</h3><p>${resource.description}</p>`))
        .addTo(map);
});

let allMarkers = []; // Array to keep track of all markers

// Initialize markers and add them to allMarkers array
resources.forEach(resource => {
    const marker = new mapboxgl.Marker({ color: resource.type === 'Food' ? 'orange' : (resource.type === 'Water' ? 'blue' : 'green') })
        .setLngLat(resource.coordinates)
        .setPopup(new mapboxgl.Popup().setHTML(`<h3>${resource.type}</h3><p>${resource.description}</p>`))
        .addTo(map);
    
    allMarkers.push({ marker: marker, type: resource.type }); // Track each marker and its type
});

// Function to filter markers
function filterMarkers(type) {
    allMarkers.forEach(({ marker, type: markerType }) => {
        if (type === 'all' || type === markerType) {
            marker.addTo(map); // Show marker
        } else {
            marker.remove(); // Hide marker
        }
    });
}
