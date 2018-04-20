#!/usr/bin/env python
# Copyright (c) 2018, SUSE Linux GmBH.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.See the License for the specific language governing permissions
# and limitations under the License.
#

from xml.etree import ElementTree as ET
import argparse
import configparser

# Need to register this namespace to ensure that the output
# does not add a prefix to the namespace. This is consistent
# with the input autoinst.xml we obtain from the nodes.

class AutoYaSTXML:
    """
    This class operates on an xml file and modifies certain networking
    parameters and writes to a new xml file. Currently the class supports
    updating MTU value, Addition of new VLAN interface and routing for ACI.
    """
    def __init__(self, inXmlFile):
        self.inXmlFile = inXmlFile
        ET.register_namespace("config", "http://www.suse.com/1.0/configns")
        self.tree = ET.ElementTree(inXmlFile)
        _begin = self.tree.parse(inXmlFile)
        self.networking = _begin.find("{http://www.suse.com/1.0/yast2ns}networking")


    def add_update_mtu_element(self, ethDevice, mtu):
        interfaces = self.networking.find("{http://www.suse.com/1.0/yast2ns}interfaces")
        interfaceList = interfaces.getchildren()
        for interface in interfaceList:
            for elt in interface.getchildren():
                if "device" in elt.attrib:
                    print "Checking for device %s" % ethDevice
                    print "Inside Tag Condition"
                    print "Text and device: %s %s" % (str(elt.text), eval(ethDevice))
                    if str(elt.text) is str(ethDevice):
                        print "Inside the condition"
                        #TODO: Add a condition to add the element only if it doesn't
                        # already exist. If it exists, just update the value to 1600.
                        # Avoid adding multiple elements
                        if not interface.find("{http://www.suse.com/1.0/yast2ns}mtu"):
                            mtuElement = ET.SubElement(interface, "{http://www.suse.com/1.0/yast2ns}mtu")
                            mtuElement.text = "%d" % mtu


    def add_vlan_interface_element(self, ethDevice, mtu, vlanId):
        # Add new VLAN interface
        interfaceExists = False

        interfaces = self.networking.find("{http://www.suse.com/1.0/yast2ns}interfaces")
        interfaceElement = ET.SubElement(interfaces, "{http://www.suse.com/1.0/yast2ns}interface")

        interfaceList = interfaces.getchildren()
        interfaceName = "vlan.%d" % vlanId

        for interface in interfaceList:
            for elt in interface.getchildren():
                if interfaceName in elt.attrib:
                    interfaceExists = True

        if not interfaceExists:
            bootproto = ET.SubElement(interfaceElement, "{http://www.suse.com/1.0/yast2ns}bootproto")
            bootproto.text = "dhcp"

            device = ET.SubElement(interfaceElement, "{http://www.suse.com/1.0/yast2ns}device")
            device.text = "vlan.%d" % vlanId

            dhcDefRoute = ET.SubElement(interfaceElement,
                "{http://www.suse.com/1.0/yast2ns}dhclient_set_default_route")
            dhcDefRoute.text = "yes"

            etherDevice = ET.SubElement(interfaceElement, "{http://www.suse.com/1.0/yast2ns}etherdevice")
            etherDevice.text = "%s" % ethDevice

            mtuElement = ET.SubElement(interfaceElement, "{http://www.suse.com/1.0/yast2ns}mtu")
            mtuElement.text = "%d" % mtu

            startMode = ET.SubElement(interfaceElement, "{http://www.suse.com/1.0/yast2ns}startmode")
            startMode.test = "auto"

            vlanIdElement = ET.SubElement(interfaceElement, "{http://www.suse.com/1.0/yast2ns}vlan_id")
            vlanIdElement.text = "%d" % vlanId


    def add_routing_element(self, vlanId, dest, gw, netmask):
        # Add Routing
        routeExists = False
        routingElement = self.networking.find("{http://www.suse.com/1.0/yast2ns}routing")
        routesElement = ET.SubElement(routingElement,
                                     "{http://www.suse.com/1.0/yast2ns}routes",
                                     attrib={"{http://www.suse.com/1.0/configns}type":"list"})

        if routesElement.find('route'):
            for route in routesElement.getchildren():
                if "vlan.%d" % vlanId in route.attrib:
                    routeExists = True

        if not routeExists:
            routeElement = ET.SubElement(routesElement, "{http://www.suse.com/1.0/yast2ns}route")

            destination = ET.SubElement(routeElement, "{http://www.suse.com/1.0/yast2ns}destination")
            destination.text = dest

            deviceElement = ET.SubElement(routeElement, "{http://www.suse.com/1.0/yast2ns}device")
            deviceElement.text = "vlan.%d" % vlanId

            gatewayElement = ET.SubElement(routeElement, "{http://www.suse.com/1.0/yast2ns}gateway")
            gatewayElement.text = gw

            netmaskElement = ET.SubElement(routeElement, "{http://www.suse.com/1.0/yast2ns}netmask")
            netmaskElement.text = netmask


    def write_tree_to_xml(self, outXmlFile):
        # Write all modified Tree data to output xml file.
        self.tree.write(outXmlFile,
                        xml_declaration=True,
                        encoding="utf-8",
                        method="xml",
                        default_namespace="http://www.suse.com/1.0/yast2ns")


def parse_and_run(node_name, config_file, input_file, output_file):
    config = configparser.ConfigParser()
    config.read(config_file)

    # get Default config parameters
    vlan_id = int(config.get('DEFAULT', 'vlan_id'))
    mtu = int(config.get('DEFAULT', 'mtu'))

    # get ethernet device for the target node
    etherDevice = config.get('aci_targets', node_name)

    # get routing parameters
    routeDest = config.get('routing', 'destination')
    routeGw = config.get('routing', 'gateway')
    routeNetmask = config.get('routing', 'netmask')

    # initialize object with the input_file
    xmlObj = AutoYaSTXML(input_file)

    # Make necessary updates to the xml file
    xmlObj.add_update_mtu_element(etherDevice, mtu)
    xmlObj.add_vlan_interface_element(etherDevice, mtu, vlan_id)
    xmlObj.add_routing_element(vlan_id, routeDest, routeGw, routeNetmask)

    # Write updated xml object into output_file
    xmlObj.write_tree_to_xml(output_file)


if __name__=="__main__":
    parser = argparse.ArgumentParser(
            prog='setup-aci-nodes',
            description="Get Data for XML files.")
    parser.add_argument('-c', '--config-file', type=str, \
            help="Absolute path for config file. If not given, the current" \
            "path is assumed to contain the file with name aci_nodes.conf.", \
            default="aci_nodes.conf")
    parser.add_argument('-n', '--node-name', type=str, \
            help="FQDN or Hostname of the node used for the xml.")
    parser.add_argument('-i', '--input-file', type=str, \
            help="Input XML file to be modified with absolute path.")
    parser.add_argument('-o', '--output-file', type=str, \
            default="/root/out_autoinst.xml", \
            help="Output XML to write the updated structure.")

    args = parser.parse_args()
    if args.input_file == None or args.node_name == None:
        parser.print_help()
        exit(0)
    else:
        parse_and_run(args.node_name,
                      args.config_file,
                      args.input_file,
                      args.output_file)
