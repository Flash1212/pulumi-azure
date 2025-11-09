# Azure Native Python Pulumi

A minimal Pulumi program for provisioning an Azure Resource Group, Storage Account, and
storage components

## Overview

This program demonstrates:

- The use of an external config.py for configuration injection
- The creation of a resource group
- The creation of a storage account/service blob properties/blob container via a resource coponent

### Output

1. blob_container_endpoints
1. connection_strings [secret]
1. storage_account_keys [secret]
1. queue_namess
1. manage_user_client_id

## Prerequisites

- An Azure subscription with sufficient permissions
- Azure CLI installed and authenticated (`az login`)
- Python 3.7 or later
