#!/usr/bin/env python
"""
Author: D. Knowles
Desc  : ROS node that outputs to the umnitsaControl board
"""
import time
import rospy
from geometry_msgs.msg import Twist
from umnitsa_msgs.msg import Joystick
import RPi.GPIO as GPIO
from math import atan2, cos, pi, sqrt
import numpy as np

class Motors():
	def __init__(self):
		"""
		initialize pins as motor outputs
		"""
		GPIO.setmode(GPIO.BOARD)          # use RasPi pin numbers

		self.DB1 = rospy.get_param('DB1') # Driver Board #1 INH
		self.M1 = rospy.get_param('M1')   # DB #1 IN1 & IN2
		self.M2 = rospy.get_param('M2')   # DB #1 IN3 & IN4
		self.DB2 = rospy.get_param('DB2') # DB #2 INH
		self.M3 = rospy.get_param('M3')   # DB #2 IN1 & IN2
		self.M4 = rospy.get_param('M4')   # DB #2 IN3 & IN4

		GPIO.setwarnings(False)     # don't show setup warnings
		# set pins as outputs and initialize to False/Low
		GPIO.setup(self.DB1,GPIO.OUT,initial=False)
		GPIO.setup(self.M1,GPIO.OUT,initial=False)
		GPIO.setup(self.M2,GPIO.OUT,initial=False)
		GPIO.setup(self.DB2,GPIO.OUT,initial=False)
		GPIO.setup(self.M3,GPIO.OUT,initial=False)
		GPIO.setup(self.M4,GPIO.OUT,initial=False)

		# setup all pwm outputs
		self.frequency = 500.0          # pwm frequency
		self.PWM_M1 = GPIO.PWM(self.M1,self.frequency)
		self.PWM_M1.start(0.0)
		self.PWM_M2 = GPIO.PWM(self.M2,self.frequency)
		self.PWM_M2.start(0.0)
		self.PWM_M3 = GPIO.PWM(self.M3,self.frequency)
		self.PWM_M3.start(0.0)
		self.PWM_M4 = GPIO.PWM(self.M4,self.frequency)
		self.PWM_M4.start(0.0)

		self.turbo = False		# turbo mode
		self.clearance = rospy.get_param('clearance') # clearance for detecting objects


	def subscribe(self):
		rospy.init_node('motors', anonymous=False)
		rospy.Subscriber('cmd_vel',Twist, self.updateOutput)
		rospy.Subscriber('commands',Joystick, self.updateSettings)
		# spin() simply keeps python from exiting until this node is stopped
		rospy.spin()

	def updateSettings(self,commands):
		if commands.TYPE == "BUTTON":
			if commands.X:
				self.turbo = not(self.turbo)

	def updateOutput(self,cmd_vel):
		# check if any toggle is not 0.0 (i.e. False)
		if cmd_vel.linear.x or cmd_vel.linear.y or cmd_vel.angular.z:
			lateral = self.lateral(cmd_vel.linear.x,cmd_vel.linear.y)
			rotation = self.rotation(cmd_vel.angular.z)
			motor_output = lateral + rotation
			if np.amax(abs(motor_output)) > 1.0:
				# scale result by highest output
				motor_output /= np.amax(abs(motor_output))
			elif self.turbo:
				# turbo mode amplifies all signals relative to highest
				motor_output /= np.amax(abs(motor_output))
			x_M1 = motor_output.item(0)
			x_M2 = motor_output.item(1)
			x_M3 = motor_output.item(2)
			x_M4 = motor_output.item(3)

			print("motor outputs: ",x_M1,x_M2,x_M3,x_M4)

			self.PWM_M1.ChangeDutyCycle(50.0 + x_M1*50.0)
			self.PWM_M2.ChangeDutyCycle(50.0 + x_M2*50.0)
			self.PWM_M3.ChangeDutyCycle(50.0 + x_M3*50.0)
			self.PWM_M4.ChangeDutyCycle(50.0 + x_M4*50.0)

			GPIO.output(self.DB1,True)   # enable DB #1
			GPIO.output(self.DB2,True)   # enable DB #2

		else:
			# disable output if right and left toggle are 0.0
			GPIO.output(self.DB1,False)
			GPIO.output(self.DB2,False)


	def rotation(self,LTOGRIGHT):
		"""
		rotate robot with the left toggle
		"""
		x = -LTOGRIGHT

		return np.array([x,x,x,x])


	def lateral(self,vel_x,vel_y):
		"""
		move robot laterally with the right toggle
		"""
		if abs(vel_x) > 0.0 or abs(vel_y) > 0.0:

			direction = atan2(vel_x,-vel_y) # direction of toggle movement
			mag = sqrt(vel_x**2+vel_y**2) # magnitude of toggle movement
			print("magnitude=",mag)

			# compute each motor throttle to move in toggle direction
			x_M1 = mag*cos(direction+pi/4.)
			x_M2 = -mag*cos(direction+pi/4.)
			x_M3 = mag*cos(direction-pi/4.)
			x_M4 = -mag*cos(direction-pi/4.)

			return np.array([x_M1,x_M2,x_M3,x_M4])
		else:
			return np.array([0.0, 0.0, 0.0, 0.0])

	def cw(self,x):
		"""
		moves robot clockwise
		input: x = throttle (0.0,1.0)
		"""
		self.PWM_M1.ChangeDutyCycle(50.0 + x*50.0)
		self.PWM_M2.ChangeDutyCycle(50.0 + x*50.0)
		self.PWM_M3.ChangeDutyCycle(50.0 + x*50.0)
		self.PWM_M4.ChangeDutyCycle(50.0 + x*50.0)

		GPIO.output(self.DB1,True)   # enable DB #1
		GPIO.output(self.DB2,True)   # enable DB #2

	def ccw(self,x):
		"""
		moves robot counter clockwise
		input: x = throttle (0.0,1.0)
		"""
		self.PWM_M1.ChangeDutyCycle(50.0 - x*50.0)
		self.PWM_M2.ChangeDutyCycle(50.0 - x*50.0)
		self.PWM_M3.ChangeDutyCycle(50.0 - x*50.0)
		self.PWM_M4.ChangeDutyCycle(50.0 - x*50.0)

		GPIO.output(self.DB1,True)   # enable DB #1
		GPIO.output(self.DB2,True)   # enable DB #2

	def forward(self,x):
		"""
		moves robot backwards
		input: x = throttle (0.0,1.0)
		"""
		self.PWM_M1.ChangeDutyCycle(50.0 - x*50.0)
		self.PWM_M2.ChangeDutyCycle(50.0 + x*50.0)
		self.PWM_M3.ChangeDutyCycle(50.0 + x*50.0)
		self.PWM_M4.ChangeDutyCycle(50.0 - x*50.0)

		GPIO.output(self.DB1,True)   # enable DB #1
		GPIO.output(self.DB2,True)   # enable DB #2

	def backward(self,x):
		"""
		moves robot forward
		input: x = throttle (0.0,1.0)
		"""
		self.PWM_M1.ChangeDutyCycle(50.0 + x*50.0)
		self.PWM_M2.ChangeDutyCycle(50.0 - x*50.0)
		self.PWM_M3.ChangeDutyCycle(50.0 - x*50.0)
		self.PWM_M4.ChangeDutyCycle(50.0 + x*50.0)

		GPIO.output(self.DB1,True)   # enable DB #1
		GPIO.output(self.DB2,True)   # enable DB #2


	def right(self,x):
		"""
		moves robot right
		input: x = throttle (0.0,1.0)
		"""
		self.PWM_M1.ChangeDutyCycle(50.0 + x*50.0)
		self.PWM_M2.ChangeDutyCycle(50.0 - x*50.0)
		self.PWM_M3.ChangeDutyCycle(50.0 + x*50.0)
		self.PWM_M4.ChangeDutyCycle(50.0 - x*50.0)

		GPIO.output(self.DB1,True)   # enable DB #1
		GPIO.output(self.DB2,True)   # enable DB #2


	def left(self,x):
		"""
		moves robot left
		input: x = throttle (0.0,1.0)
		"""
		self.PWM_M1.ChangeDutyCycle(50.0 - x*50.0)
		self.PWM_M2.ChangeDutyCycle(50.0 + x*50.0)
		self.PWM_M3.ChangeDutyCycle(50.0 - x*50.0)
		self.PWM_M4.ChangeDutyCycle(50.0 + x*50.0)

		GPIO.output(self.DB1,True)   # enable DB #1
		GPIO.output(self.DB2,True)   # enable DB #2

	def disable(self):
		"""
		disable both motor driver boards
		"""
		GPIO.output(self.DB1,False)   # disable DB #1
		GPIO.output(self.DB2,False)   # disable DB #2

if __name__ == '__main__':
	try:
		subscriber = Motors()
		subscriber.subscribe()
	except rospy.ROSInterruptException:
		subscriber.PWM_M1.stop()
		subscriber.PWM_M2.stop()
		subscriber.PWM_M3.stop()
		subscriber.PWM_M4.stop()
		subscriber.disable()