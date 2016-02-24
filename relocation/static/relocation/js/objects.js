/**
 * Created by dsx on 2/15/2016.
 */
object_map = L.map('object_map')

L.tileLayer('http://{s}.tile.osm.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors'
}).addTo(object_map);