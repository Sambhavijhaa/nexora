import logging
import os
import re
import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, g, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token, get_jwt, get_jwt_identity, jwt_required
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint, func
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()
# Backend restored to production-compatible implementation.
# Invitation-link changes will be added only after a safe patch is available.
