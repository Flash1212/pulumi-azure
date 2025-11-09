# Azure Native Python Pulumi Template

A minimal Pulumi program for provisioning an Azure Resource Group, Storage Account, managed system account and function app using the Azure Native provider with Python.

## Overview

This program demonstrates:

- The use of an external config.py for configuration injection
- The creation of a resource group
- The creation of a storage account/service blob properties/blob container via a resource coponent
- The creation of an operational insights workspace
- The creation of an app insights component
- The creation of a user assigned identity
- The assignment of multiple roles to the managed identity and executing user
- The creation of an App Service Plan
- The creation of a WebApp focused on Funtion Apps.

### Output

1. default_host_name
1. service_plan_name
1. blob_container_url
1. connection_string [secret]
1. storage_account_keys [secret]
1. queue_name

## Prerequisites

- An Azure subscription with sufficient permissions
- Azure CLI installed and authenticated (`az login`)
- Python 3.7 or later
