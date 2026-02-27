#!/usr/bin/env python3
"""
Run server with better error logging
"""
import logging
import sys
import os

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[
        logging.FileHandler('server.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Add path
sys.path.append(os.path.dirname(__file__))

try:
    from server import app
    logger = logging.getLogger(__name__)
    
    logger.info("Starting server...")
    
    # Run with debug mode to catch errors
    app.run(host='0.0.0.0', port=5001, debug=True, threaded=False)
    
except Exception as e:
    logger.error(f"Fatal error starting server: {e}")
    import traceback
    traceback.print_exc()
