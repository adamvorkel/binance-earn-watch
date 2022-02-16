#!/bin/bash

set -e

gcloud functions deploy binance-earn-check --env-vars-file .env.yaml