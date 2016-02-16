/**
 * Created by dsx on 2/15/2016.
 */
parcel_map = L.map('parcel_map')

L.tileLayer('http://{s}.tile.osm.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors'
}).addTo(parcel_map);
