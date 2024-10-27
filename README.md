## Install Guide
Download and unzip
Run in PyCharm to install dependancies
Hopefully It'll run :D


## Inspiration
Coming from Indonesia, (a tropical country located right on the Ring of Fire,) we're not strangers to natural disasters of all kinds, be it floods, earthquakes, tsunamis, or even volcanic eruptions. We've experienced firsthand how chaotic and disorganized rescue efforts can be in crises situations, which will become even more frequent due to the presence of climate change. So, we thought up AidLink as a community-based approach to disaster mitigation.

## What it does
AidLink is a map-based platform designed to connect disaster survivors with essential aid resources and emergency responders. Powered by OpenStreetMaps and Firebase, AidLink provides survivors with up-to-date access to nearby shelters, amenities, and safe routes, while allowing both survivors and aid providers to actively contribute by marking inaccessible roads and adding shelters. 
During natural disasters, when every second counts, AidLink aims to help people adapt to real-world conditions, ensuring those in need can find life-saving assistance when they need it most.

## How we built it
We pulled map data from OpenStreetMaps API and added several search features, then hosted it on a website using Firebase.

## Challenges we ran into
- We had no experience using databases, which was a big hassle when trying to request data from OSM and adding custom markers
- Figuring out how to connect the front-end website and back-end server code
- Figuring out how to deploy the website, which is still only able to be run locally due to the big cache size.

## Accomplishments that we're proud of
- Making the thing even run at all!
- Implementing Djikstra with custom roadblocks.
- Adding custom shelters and roadblocks to a real-time database.
- (Somewhat) integrating the website and the server.

## What we learned
We learned too much😔. We started with no experience using Github, Firebase, OpenStreetMaps API, Flask, pretty much everything apart from the programming languages, and now we do!

## What's next for AidLink - Tech for Natural Disaster Management
A lot of stuff could be added:
- Actually deploying the website 
- More intuitive marker and shelter additions.
- Reducing the filesize and computation time
- Survivors being able to request aid or certain resources
- Shelter inventory tracking and demand prediction based on survivor requests
