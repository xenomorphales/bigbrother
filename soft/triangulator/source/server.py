#!/usr/bin/env python
# coding: utf-8

import math
import socket
import sys
import time
import numpy


def anglesToVector(angle_cam, angle_mark):
	# angle_cam is the orientation of the camera
	#  >  0 is to the right
	#  >  1 is to the bottom
	#  > -1 is to the top
	#  >  2 is to the left
	# angle_mark is point of view from Camera.
	# -1 means 90° on its left, 0 is forward, 1 is 90° on its right.
	angle = angle_cam + angle_mark
	rad_angle = math.pi * angle / 2
	cosa = math.cos(rad_angle)
	sina = math.sin(rad_angle)
	return numpy.array([cosa, sina])

def areVectorsCollinear(v1, v2):
	# vectors must be unitary, returns true for approx less than 6 degrees
	return abs(v1[0]*v2[1] - v1[1]*v2[0]) < 0.1

def lineFrom2Points(p1, p2):
	A = p1[1] - p2[1]
	B = p2[0] - p1[0]
	C = p2[0]*p1[1] - p1[0]*p2[1]
	return A, B, C

def centroid(poses, radiuses):
	# warning! take care that the greater the radius, the lower the quality of information
	posSum = 0
	coefSum = 0
	for i in range(len(radiuses)):
		coef = 1.0/radiuses[i]
		posSum += poses[i] * coef
		coefSum += coef
	return map(int, posSum / coefSum)

def distPos(p1, p2):
	dx = p1[0] - p2[0]
	dy = p1[1] - p2[1]
	return math.sqrt(dx*dx + dy*dy)

def isInTable(point, radius):
	# returns true if the point is in the table.
	# we accept a point slightly out of the table depending the accuracy radius
	minMaxX = 1500 + radius/2
	minY = -radius/2
	maxY = 2000 + radius/2
	return point[0] > -minMaxX and point[0] < minMaxX and point[1] > minY and point[1] < maxY

def posFrom3Cameras(cams, markers, curTime):
	pos12, rad12 = posFrom2Cameras(cams[0:2], markers[0:2], curTime)
	if rad12 < 0:
		return [], -1
	pos23, rad23 = posFrom2Cameras(cams[1:3], markers[1:3], curTime)
	if rad23 < 0:
		return [], -1
	pos13, rad13 = posFrom2Cameras([cams[0], cams[2]], [markers[0], markers[2]], curTime)
	if rad13 < 0:
		return [], -1
	res = centroid([pos12, pos23, pos13], [rad12, rad23, rad13])
	# now let's make sure we are not to far from each position
	dist12 = distPos(res, pos12)
	dist23 = distPos(res, pos23)
	dist13 = distPos(res, pos13)
	if dist12 > rad12 + 200 or dist23 > rad23 + 200 or dist13 > rad13 + 200:
		return [], -1
	# radxy is at best ~80, and at worst ~550
	# radSum should be between 240 and 1650
	# let's make some more magic to compute the final radius
	# let's take the sum divided by 8 (so between 30 and 200)
	# the distances should be between 40mm and 400mm
	# let's divide them by 4 (to have something between 10mm and 100mm)
	# => final radius should be between 40mm and 300mm
	radSum = rad12 + rad23 + rad13
	distSum = dist12 + dist23 + dist13
	return res, radSum/8 + distSum/4

def posFrom2Cameras(cams, markers, curTime):
	# x = x1 + k1*vx1
	#   = x2 + k2*vx2
	# y = y1 + k1*vy1
	#   = y2 + k2*vy2
	pos1, rad1, vec1 = posFrom1Camera(cams[0], markers[0], curTime)
	pos2, rad2, vec2 = posFrom1Camera(cams[1], markers[1], curTime)
	if distPos(pos1, pos2) > rad1 + rad2 + 400:
		# don't bother to go further, if the approximate points viewed by the cameras are to far from each other
		return [], -1
	# first, check if vectors are (slightly) collinear because line intersection does not work in this case
	if areVectorsCollinear(vec1, vec2):
		# let's get the centroid of the 2 approx positions, and make sure this is not absurd
		#print "collinear!"
		dist12 = distPos(pos1, pos2)
		if dist12 > 800:
			# information not good enough
			#print "collinear but too far ", res, pos1, pos2
			return [], -1
		res = numpy.array(centroid([pos1, pos2], [rad1, rad2]))
		# rad1 and rad2 are at best ~100, and at worst ~900
		# dist12/2 is expected to be somewhere between 50mm and 400mm
		# (rad1+rad2)/4 is between 50mm and 450mm
		radius = 30 + dist12/2 + (rad1 + rad2)/4
		return res, radius
	
	# line intersection
	A1, B1, C1 = lineFrom2Points(cams[0].pos, pos1)
	A2, B2, C2 = lineFrom2Points(cams[1].pos, pos2)
	D  = A1*B2 - B1*A2
	Dx = C1*B2 - B1*C2
	Dy = A1*C2 - C1*A2
	if D == 0:
		# lines do not intersect
		#print "det is 0"
		return [], -1
	res = numpy.array([ Dx/float(D), Dy/float(D) ])
	dist1 = distPos(pos1, res)
	dist2 = distPos(pos2, res)
	if dist1 > rad1 + 300 or dist2 > rad2 + 300:
		#print res, pos1, pos2
		#print "pos1 res pos2 too far " + str(distPos(pos1, res)) + " " + str(distPos(pos2, res))
		return [], -1

	# rad1 and rad2 are at best ~100, and at worst ~900
	# here some magic, let's take the sum divided by 8 (so between 25 and 225)
	# the sum of distances is expected somewhere to be between 100mm and 1200mm
	# the sum divided by 4 is expected to be between 25mm and 300mm
	# which means 50mm at best, 525mm at worst, => let's add a 30mm flat malus
	radius = 30 + (rad1 + rad2) / 6 + (dist1 + dist2) / 4
	return res, radius

def posFrom1Camera(cam, marker, curTime):
	diffTime = curTime - marker.last_update
	vector = anglesToVector(cam.angle, marker.angle)
	pos = map(int, cam.pos + vector * marker.distance)
	# the closer the robot to the camera, the more accurate the distance information
	# if the robot detection is recent, the information is more accurate (consider robot's speed is ~200mm/sec)
	# for example:
	#  > 1 second old + 3500 mm from camera => worst case => radius = 200+700 = 900 mm
	#  > 0.1 second old + 400 mm from camera => almost best case => radius = 20+80 = 100 mm
	#  > 0.5 second old + 500 mm from camera => close but old => radius = 100+100 = 200 mm
	#  > 0.2 second old + 2500 mm from camera => far but recent => radius = 40+500 = 540 mm
	#  > 0.3 second old + 1500 mm from camera => medium case => radius = 60+300 = 360 mm
	radius = int(diffTime * 200 + marker.distance * 0.2)
	return numpy.array(pos), radius, vector

class Robot:
	def __init__(self, id):
		self.id = id
		self.idstr = " R" + str(id) + " "
		self.pos = [0, 0]
		self.radius = 0
		self.cameras = []

	def addCamera(self, camera):
		self.cameras.append(camera)

	def updatePos(self, curTime):
		detectedCameras = []
		detectedMarkers = []
		for cam in cameras:
			diffTime = curTime - cam.markers[self.id].last_update
			if diffTime < 1:
				# if diffTime is > 1 second, consider information is out of date
				detectedCameras.append(cam)
				detectedMarkers.append(cam.markers[self.id])
				#print cam.pos, cam.angle
				#cam.markers[self.id].debug()
		if len(detectedCameras) == 0:
			# robot has not been detected by any camera
			return False

		if len(detectedCameras) == 1:
			# only one camera... let's try anyway to send some information
			self.pos, self.radius, vec = posFrom1Camera(detectedCameras[0], detectedMarkers[0], curTime)
			return self.radius >= 0 and isInTable(self.pos, self.radius)

		if len(detectedCameras) == 2:
			# classic case: simple line intersection
			self.pos, self.radius = posFrom2Cameras(detectedCameras, detectedMarkers, curTime)
			return self.radius >= 0 and isInTable(self.pos, self.radius)

		# best scenario, the robot has been detected by the 3 cameras!
		self.pos, self.radius = posFrom3Cameras(detectedCameras, detectedMarkers, curTime)
		return self.radius >= 0 and isInTable(self.pos, self.radius)

	def getMessage(self):
		return self.idstr + str(self.pos[0]) + " " + str(self.pos[1]) + " " + str(self.radius)

	def debug(self):
		print ">> I'm robot #" + str(self.id)
		print "pos    = " + str(self.pos)
		print "radius = " + str(self.radius)
		print "I know " + str(len(self.cameras)) + " cameras"
		print ""

class Marker:
	def __init__(self, id):
		self.id = id
		self.angle = 0
		self.distance = 0
		self.confidence = 0
		self.last_update = 0

	def debug(self):
		print ">> I'm marker #" + str(self.id)
		print "angle    = " + str(self.angle)
		print "distance = " + str(self.distance)
		print "conf     = " + str(self.confidence)
		print "last_upd = " + str(self.last_update)
		print ""

class Camera:
	def __init__(self, id, pos, angle):
		self.id = id
		self.pos = numpy.array(map(float, pos))
		self.angle = float(angle)
		self.markers = []
		for i in range(4):
			self.markers.append(Marker(i))

	def update(self, msg):
		fields = msg.split(" ")
		if self.id != int(fields[0]):
			print "ERROR camera id " + fields[0] + " != " + str(self.id)
			return
		print "camera_id: " + str(self.id)
                marker = []
		for i in range(len(fields) - 1):
			if i % 4 == 0:
				marker = self.markers[int(fields[i + 1])]
			elif i % 4 == 1:
				marker.x = float(fields[i + 1])
			elif i % 4 == 2:
				marker.height = float(fields[i + 1])
			elif i % 4 == 3:
				marker.confidence = float(fields[i + 1])
				marker.last_update = time.time()

	def debug(self):
		print ">> I'm camera #" + str(self.id)
		print "pos   = " + str(self.pos)
		print "angle = " + str(self.angle)
		print "I know " + str(len(self.markers)) + " markers:"
		for mark in self.markers:
			mark.debug()
		print ""

####################
####### main #######
####################

# global var config
config_file_name = "../config/config.txt"
UDP_PORT = 0
cameras = []
robots = []
last_time_update = 0

# parse configuration
try:
	config_file = open(config_file_name)
	for line in config_file:
		if line.startswith("#") or line == "\n":
			continue
		token, value = line.split("=")
		if token == "UDP_PORT":
			UDP_PORT = int(value)
		elif token.startswith("POSITION_"):
			pos_id = int(token.replace("POSITION_", ""))
			if pos_id < 0 or pos_id > 2:
				raise SyntaxError("Invalid position id: " + token)
			coords = value.split(",")
			if len(coords) != 3:
				raise SyntaxError("Invalid position value: " + value)
			cameras.append(Camera(pos_id, coords[0:2], coords[2]))
		else:
			raise SyntaxError("Unrecognized token:" + token)
	if UDP_PORT == 0:
		raise SyntaxError("UDP_PORT has not been defined")
except Exception as e:
	print repr(e)
	sys.exit("Error reading config file " + config_file_name)
config_file.close()

# init robots
for i in range(4):
	robots.append(Robot(i))
	for cam in range(3):
		robots[i].addCamera(cameras[cam])

#### data to test perf and corner cases
cameras[0].markers[0].last_update = 10
cameras[1].markers[0].last_update = 10
cameras[2].markers[0].last_update = 10
cameras[0].markers[0].angle = 0.49
cameras[1].markers[0].angle = -0.49
cameras[2].markers[0].angle = 0.01
cameras[0].markers[0].distance = 800
cameras[1].markers[0].distance = 1000
cameras[2].markers[0].distance = 2582
cameras[0].markers[1].last_update = 10
cameras[1].markers[1].last_update = 10
cameras[2].markers[1].last_update = 10
cameras[0].markers[1].angle = 0.49
cameras[1].markers[1].angle = -0.49
cameras[2].markers[1].angle = 0.01
cameras[0].markers[1].distance = 800
cameras[1].markers[1].distance = 1000
cameras[2].markers[1].distance = 2582
cameras[0].markers[2].last_update = 10
cameras[1].markers[2].last_update = 10
cameras[2].markers[2].last_update = 10
cameras[0].markers[2].angle = 0.49
cameras[1].markers[2].angle = -0.49
cameras[2].markers[2].angle = 0.01
cameras[0].markers[2].distance = 800
cameras[1].markers[2].distance = 1000
cameras[2].markers[2].distance = 2582
cameras[0].markers[3].last_update = 10
cameras[1].markers[3].last_update = 10
cameras[2].markers[3].last_update = 10
cameras[0].markers[3].angle = 0.49
cameras[1].markers[3].angle = -0.49
cameras[2].markers[3].angle = 0.01
cameras[0].markers[3].distance = 800
cameras[1].markers[3].distance = 1000
cameras[2].markers[3].distance = 2582
#print robots[0].updatePos(10.1)
#print robots[0].getMessage()
#sys.exit()

# print configuration
for rob in robots:
	rob.debug()
for cam in cameras:
	cam.debug()

if len(cameras) != 3:
	sys.exit("3 cameras must be defined")

# prepare socket
sock_cameras = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
sock_cameras.bind(("", UDP_PORT))
sock_cameras.settimeout(0)

# last info received from cameras

print ""
print "Listenning port " + str(UDP_PORT) + "..."
while True:
	time.sleep(0.05) # avoid to burn 100% CPU... and give a chance to a CtrlC :)
	try:
		# if enough time has elapsed since last update, we can resend our info to the robots
		now = time.time()
		diff = now - last_time_update
		if diff > 0.15:
			print str(now)
			msg = ""
			for rob in robots:
				if rob.updatePos(10.3):
					msg += rob.getMessage()
			if len(msg) > 0:
				# send message to robots
				print "SEND: " + msg
			last_time_update = now

		# let's see if we received any data from cameras
		for i in range(len(cameras)):
			data, addr = sock_cameras.recvfrom(1024)
			cam_id = int(data[0])
			cameras[cam_id].update(data)
		#cameras[cam_id].debug()

		# listen to any client who wants information
	except:
		pass
