#!/usr/bin/env python3
# Copyright (c) 2016 E.ON Off Grid Solutions GmbH
# Original Author: Chen Chiang (chen.chiang@eon-offgrid.com)

# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import requests
import json
import logging
import datetime
import time

# for loading configuration files
from configobj import ConfigObj

from os import path

class Higeco:

  def __init__(self,url,username,password):
    # use logging instead of print for debugging/info messages
    logging.basicConfig(level=logging.DEBUG)
    self.log = logging.getLogger(__name__)
    # initialize the class session object
    self.session = requests.Session()
    # default timeouts
    self.TIMEOUT = 12
    if url[len(url)-1] != '/':
      self.domain = url + '/'
    else:
      self.domain = url
    # login
    self.__load_token()
    self.username = username
    self.password = password
    self.__login()

  ###################################################

  #                Internal Functions               #

  ###################################################
  """
  Input:
    response status code
  Output:
    True/False based on status code + log messages if failure
  """
  def __verify_response(self,rstatus):
    if rstatus == 200:
      return True
    elif rstatus == 400:
      self.log.error("Bad request")
      return False
    elif rstatus == 401:
      self.log.error("Unauthorized")
      return False
    elif rstatus == 404:
      self.log.error("Not found")
      return False
    elif rstatus == 500:
      self.log.error("Internet server error")
    return False

  """
  Input:
    none
  Output:
    default token for authorization process
  """
  def __load_token(self):
    conf = path.dirname(path.realpath(__file__)) + "/higecotoken.conf"
    try:
      self.config = ConfigObj(conf,file_error=True)
      self.default_token = self.config["token"]
    except OSError as msg:
      #invalid config file 
      self.log.error(msg)
      return None

  """
  Input:
    none
  Function:
    Login, on success sets the class variable self.token used in future requests.
    On failure the self.token variable will be NoneType. And generating a timestamp as token updating reference.
  Output:
    True for success and false on failure
  """
  def __login(self):
    # first try to login in with username and password
    resp = self.auth_password()
    if resp:
      self.log.debug("login via username and password")
      return True
    else:
      #login via username and password failed
      resp_n = self.auth_token()
      if resp_n:
        self.log.debug("login via default token")
        return True
      else:
        self.log.error("login failed")
        return False

  """
  Input:
    none
  Output:
    True for success and False for failure
  """
  def __token_update(self):
   # re-login to get token and timestamp updated
    resp = self.__login() 
    return resp

  """
  Input:
    none
  Function:
    checking the valid time of token
  Output:
    True when need to update (invalid token or soon expiring token)
    False when no need to update
  """
  def __valid_check(self):
    # first check wether the token is still valid 
    timeNow = time.mktime(datetime.datetime.utcnow().timetuple())
    if timeNow - self.timestamp > 7200:
    # token not valid, update
      self.__token_update()
      return True
    elif timeNow - self.timestamp > 6600:
    # token is about to be invalid, update 
      self.__token_update()
      return True
    else:
    # no need to update
      return False

  """
  Input:
    url
  Output:
    json data in list format or none on failure 
  """
  def __http_get_json(self,url):
    headers = {'authorization':self.token}
    try:
      response = self.session.request("GET",url,headers = headers,timeout=self.TIMEOUT)
      if self.__verify_response(response.status_code):
        response_json = json.loads(response.text)
        return response_json
      else:
        return None
    except requests.exceptions.ConnectionError as msg:
      # no working DNS
      self.log.error(msg)
      return None

  """
  Input:
    url
    query data
  Output:
    True for success, False for failure
  """
  def __http_post_json(self,url,data):
    try:
      response = self.session.request('POST',url,data=json.dumps(data),timeout=self.TIMEOUT)
      if self.__verify_response(response.status_code):
        response_json = json.loads(response.text)
        self.log.debug("Login successful.")
        self.token = response_json.get('token')
        self.timestamp = time.mktime(datetime.datetime.utcnow().timetuple())
        return True
      else:
        self.token = None
        self.timestamp = None
        return False
    except requests.exceptions.ConnectionError as msg:
      # no working DNS
      self.log.error(msg)
      return False

  ###################################################

  #                1. Authentication                #

  ###################################################

  """
  Input:
    none
  Function:
    authorization via username and password
  Output:
    token, timestamp
  """
  def auth_password(self):
    url = self.domain + "api/v1/authenticate"
    data = {'username': self.username, 'password': self.password}
    resp = self.__http_post_json(url,data)
    return resp

  """
  Input:
    none
  Function:
    authorization via default token
  Output:
    token, timestamp
  """
  def auth_token(self):
    url = self.domain + "api/v1/authenticate"
    data = {'apiToken': self.default_token}
    resp = self.__http_post_json(url,data)
    return resp

###########################################################

#                 2. Api_Plants                           #

###########################################################

  """
  Input:
    none
  Function:
    get plant list
  Output:
    Returns JSON data in list format on the plant (site) list
  """
  def get_plant_list(self):
    url = self.domain + "api/v1/plants" 
    resp = self.__http_get_json(url)
    return resp

  """
  Input:
    plantId (integer, or integer as string)
  Function:
    get plant description
  Output:
    Returns JSON data in list format on the plant (site) list
  """
  def get_plant_descrip(self,plantId):
    url = self.domain + "api/v1/plants/" + str(plantId) 
    resp = self.__http_get_json(url)
    return resp

  """
  Input:
    None
  Function:
    get plant ids
  Output:
    Returns a list with all Plant IDs that the user has access to (can also be accessed by looping through get_plants data)
  """
  def get_plant_ids(self):
    plants = self.get_plant_list()
    plant_ids = []
    for plant in range(0,len(plants)):
      plant_ids.append(plants[plant]["id"])
    return plant_ids

###########################################################

#                3. Api_Devices                           #

###########################################################

  """
  Input:
    plantId (integer, or integer as string)
  Function:
    get device list
  Output:
    Returns JSON data in list format on the specified plant (site)
  """
  def get_device_list(self,plantId):
    url = self.domain + "api/v1/plants/" + str(plantId) + "/devices" 
    resp = self.__http_get_json(url)
    return resp

  """
  Input:
    plantId (integer, or integer as string)
    deviceId (string) 
  Function:
    get device description
  Output:
    Returns JSON data in list format on the plant (site) list
  """
  def get_device_descrip(self,plantId,deviceId):
    url = self.domain + "api/v1/plants/" + str(plantId) + "/devices/" + str(deviceId)
    resp = self.__http_get_json(url)
    return resp

###########################################################

#                4. Api_Log                               #

###########################################################

  """
  Input:
    plantId (integer, or integer as string)
    deviceId (string)
  Output:
    Returns JSON data in list format on the specified device
  """
  def get_log_list(self,plantId,deviceId):
    url = self.domain + "api/v1/plants/" + str(plantId) + "/devices/" + str(deviceId) + "/logs/"
    resp = self.__http_get_json(url)
    return resp

  """
  Input:
    plantId (integer, or integer as string)
    deviceId (string)
    logId (integer, or integer as string)
  Output:
    Returns JSON data in list format on the specified device
  """
  def get_log_descrip(self,plantId,deviceId,logId):
    url = self.domain + "api/v1/plants/" + str(plantId) + "/devices/" + str(deviceId) + "/logs/" + str(logId)
    resp = self.__http_get_json(url)
    return resp

###########################################################

#                5. Api_Items                             #

###########################################################

  """
  Input:
    plantId (integer, or integer as string)
    deviceId (string)
    logId (integer, or integer as string)
  Output:
    Returns JSON data in list format on the specified device
  """
  def get_item_list(self,plantId,deviceId,logId):
    url = self.domain + "api/v1/plants/" + str(plantId) + "/devices/" + str(deviceId) + "/logs/" + str(logId) + "/items/"
    resp = self.__http_get_json(url)
    return resp

  """
  Input:
    plantId (integer, or integer as string)
    deviceId (string)
    logId (integer, or integer as string)
    itemId (integer, or integer as string)
  Output:
    Returns JSON data in list format on the specified device
  """
  def get_item_descrip(self,plantId,deviceId,logId,itemId):
    url = self.domain + "api/v1/plants/" + str(plantId) + "/devices/" + str(deviceId) + "/logs/" + str(logId) + "/items/" + str(itemId)
    resp = self.__http_get_json(url)
    return resp

###########################################################

#                6. Api_Data                              #

###########################################################

  """
  Input:    
    plantId (integer, or integer as string)
    deviceId (string)
    logId (integer, or integer as string)
  Output:
    Returns JSON data in list format on the specified device
  """
  def get_log_data(self,plantId,deviceId,logId):
    url = self.domain + "api/v1/getLogData/" + str(plantId) + "/" + str(deviceId) + "/" + str(logId)
    resp = self.__http_get_json(url)
    return resp

  """
  Input:    
    plantId (integer, or integer as string)
    deviceId (string)
    logId (integer, or integer as string)
    itemId (integer, or integer as string)
  Output:
    Returns JSON data in list format on the specified device
  """
  def get_item_data(self,plantId,deviceId,logId,itemId):
    url = self.domain + "api/v1/getLogData/" + str(plantId) + "/" + str(deviceId) + "/" +  str(logId) + "/" +  str(itemId)
    resp = self.__http_get_json(url)
    return resp

  """
  Input:    
    plantId (integer, or integer as string)
    deviceId (string)
    logId (integer, or integer as string)
  Output:
    Returns JSON data in list format on the specified device
  """
  def get_last_values(self,plantId,deviceId,logId):
    url = self.domain + "api/v1/getLastValue/" + str(plantId) + "/" + str(deviceId) + "/" + str(logId)
    resp = self.__http_get_json(url)
    return resp

  """
  Input:    
    plantId (integer, or integer as string)
    deviceId (string)
    logId (integer, or integer as string)
    itemId (integer, or integer as string)
  Output:
    Returns JSON data in list format on the specified device
  """
  def get_last_value(self,plantId,deviceId,logId,itemId):
    url = self.domain + "api/v1/getLastValue/" + str(plantId) + "/" + str(deviceId) + "/" + str(logId) + "/" + str(itemId)
    resp = self.__http_get_json(url)
    return resp

###########################################################

#                 Get_Desired_Data                        #

###########################################################

  """
  Input:
    plant_id (integer, or integer as string)
    parameter(string list, e.g.: ["Battery voltage","Output power"])
  Output:
    Returns a dict of data with the specified parameters
  """
  def get_data(self,plant_id,parameters):
    #check if the token is still valid
    self.__valid_check()

    deviceID_wanted = []
    logID_wanted = []
    valuesList_wanted = []
    values_wanted = []
#    data = []
    resp_data = {}
    device_json = self.get_device_list(plant_id)
    for device in range(0,len(device_json)):
      deviceID_wanted.append(device_json[device]["id"])
    for device in range(0,len(deviceID_wanted)):
      log_json = self.get_log_list(plant_id,deviceID_wanted[device])
      for log in range(0,len(log_json)):
        logID_wanted.append(log_json[log]["id"])
        for value in range(0,len(logID_wanted)):
          lastValues_json = self.get_last_values(plant_id,deviceID_wanted[device],logID_wanted[value])
          itemValues = lastValues_json['items']
          for item in range(0,len(itemValues)):
            valuesList_wanted.append(itemValues[item]['name'])
            values_wanted.append(itemValues[item]['value'])
#    resp_data.append(itemValues[item]['utc'])i
    resp_data.update({'Timestamp':itemValues[item]['utc']})
    for para in parameters:
      if para in valuesList_wanted:
#        data.append(values_wanted[valuesList_wanted.index(para)])
        resp_data.update({para:values_wanted[valuesList_wanted.index(para)]})
      else:
        resp_data.update({para: ''})
    return resp_data

