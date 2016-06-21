# py-higeco
Python bindings to use the API published by Higeco S.r.l

This API code is used to get data of connected devices (like inverters) from Higeco Datalogger GWC.

In oder to use it, you will need the login information from Higeco about your certain project. And also put your default token into the configuration file.

The funtions to get the data from top layer to bottom layer are all given (from "Plant" -> "Device" -> "Log" -> "Item" -> "Last Value"), in case you want to take a close look.

But the easiest way to use it, is calling the get_data function by giving Plant_ID(your unique project ID from Higeco side) and the wanted parameters.

