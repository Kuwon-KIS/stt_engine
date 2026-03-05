#!/usr/bin/env python3
"""
Download SheetJS library for offline use.
Runs during Docker build to download xlsx.full.min.js to local static folder.
"""

import os
import sys
import urllib.request
import urllib.error

def download_sheetjs():
    """Download SheetJS library to static/lib directory"""
    
    # Create static/lib directory if it doesn't exist
    static_lib_dir = os.path.join(os.path.dirname(__file__), '..', 'web_ui', 'static', 'lib')
    os.makedirs(static_lib_dir, exist_ok=True)
    
    # SheetJS CDN URL
    sheetjs_url = 'https://cdn.sheetjs.com/xlsx-0.20.1/package/dist/xlsx.full.min.js'
    output_file = os.path.join(static_lib_dir, 'xlsx.full.min.js')
    
    print(f'Downloading SheetJS from {sheetjs_url}...')
    
    try:
        # Download with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f'Attempt {attempt + 1}/{max_retries}...', file=sys.stderr)
                urllib.request.urlretrieve(sheetjs_url, output_file)
                file_size = os.path.getsize(output_file)
                print(f'✓ Downloaded successfully to {output_file} ({file_size:,} bytes)')
                return True
            except (urllib.error.URLError, urllib.error.HTTPError) as e:
                if attempt < max_retries - 1:
                    print(f'  Retry after error: {e}', file=sys.stderr)
                    continue
                else:
                    raise
    
    except Exception as e:
        print(f'✗ Failed to download SheetJS: {e}', file=sys.stderr)
        print(f'Note: This is expected if running in offline mode.', file=sys.stderr)
        print(f'Excel export will be disabled. CSV export will still work.', file=sys.stderr)
        return False

if __name__ == '__main__':
    success = download_sheetjs()
    sys.exit(0 if success else 1)
