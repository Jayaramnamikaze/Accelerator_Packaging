"""
Tableau Workbook Download and Extraction Module

This module handles:
1. Downloading Tableau workbooks from the server OR processing local TWB files
2. Extracting XML content and splitting workbooks by dashboard
3. Generating JSON output using MigrationEngine
"""

import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from dotenv import load_dotenv, dotenv_values
import tableauserverclient as TSC
from slugify import slugify
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Add src to path for MigrationEngine
sys.path.insert(0, str(Path(__file__).parent / "src"))
from tableau_to_looker_parser.core.migration_engine import MigrationEngine


def extract_twb_xml(file_path):
    """
    Extract XML content from a Tableau workbook file (.twb or .twbx).
    
    Args:
        file_path: Path to the .twb or .twbx file
        
    Returns:
        str: XML content as string, or empty string if extraction fails
    """
    try:
        if zipfile.is_zipfile(file_path):
            with zipfile.ZipFile(file_path, 'r') as z:
                twb_files = [f for f in z.namelist() if f.endswith('.twb')]
                if not twb_files:
                    return ""
                with z.open(twb_files[0]) as f:
                    return f.read().decode("utf-8", errors="ignore")
        else:
            return Path(file_path).read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        print(f"Failed to read {file_path}: {e}")
        return ""


def get_dashboard_xml(xml_string):
    """
    Split workbook XML into individual dashboard XMLs.
    
    Args:
        xml_string: Complete workbook XML as string
        
    Returns:
        dict: Dictionary mapping dashboard names to their XML strings
    """
    try:
        tree = ET.ElementTree(ET.fromstring(xml_string))
        root = tree.getroot()
    except ET.ParseError as e:
        raise e

    dashboard_list = root.findall(".//dashboard")
    if dashboard_list is None or len(dashboard_list) == 0:
        print("No Dashboard found")
        return {}
    
    # Remove all <thumbnails>
    for thumbnails in root.findall("thumbnails"):
        root.remove(thumbnails)

    overall_worksheet_set = set()
    for worksheet in root.findall('.//worksheet'):
        worksheet_name = worksheet.get("name", None)
        if worksheet_name is not None:
            overall_worksheet_set.add(worksheet_name)

    dashboard_map = {}
    for dashboard in dashboard_list:
        dashboard_name = dashboard.get("name", None)
        if dashboard_name is None:
            continue
        temp = {
            "dashboard_xml": ET.tostring(dashboard, encoding='utf-8').decode('utf-8'),
            "worksheets": set()
        }
        zones = dashboard.findall(".//zones")
        if zones:
            for zone in zones[0].findall(".//zone"):
                if zone.get('name') in overall_worksheet_set and zone.get('param', None) is None:
                    temp["worksheets"].add(zone.get('name'))
        temp["worksheets"] = list(temp["worksheets"])
        dashboard_map[dashboard_name] = temp

    temp_xmlstring = ET.tostring(root, encoding='utf-8').decode('utf-8')
    final_dashboard_xml = {}
    for dashboard_name in dashboard_map:
        temp_root = ET.fromstring(temp_xmlstring)
        root_dashboards = temp_root.find(".//dashboards")
        for xml_dashboard in list(root_dashboards.findall("dashboard")):
            if xml_dashboard.get("name") != dashboard_name:
                root_dashboards.remove(xml_dashboard)
        root_worksheets = temp_root.find(".//worksheets")
        for xml_worksheet in list(root_worksheets.findall("worksheet")):
            if xml_worksheet.get("name") not in dashboard_map[dashboard_name]["worksheets"]:
                root_worksheets.remove(xml_worksheet)
        final_dashboard_xml[dashboard_name] = ET.tostring(temp_root, encoding='utf-8').decode('utf-8')
    return final_dashboard_xml


def generate_json_from_twb(twb_file_path: str, output_dir: str = "output") -> dict:
    """
    Generate JSON from a local TWB file using MigrationEngine.
    
    Args:
        twb_file_path: Path to .twb or .twbx file
        output_dir: Directory to save JSON output
        
    Returns:
        dict: Migration result with statistics
    """
    twb_path = Path(twb_file_path)
    if not twb_path.exists():
        raise FileNotFoundError(f"TWB file not found: {twb_file_path}")
    
    if twb_path.suffix.lower() not in ['.twb', '.twbx']:
        raise ValueError(f"Invalid file type. Expected .twb or .twbx, got: {twb_path.suffix}")
    
    print(f"\n📄 Processing local TWB file: {twb_path.name}")
    print(f"   Path: {twb_path.absolute()}")
    
    # Initialize MigrationEngine
    print("\n🔧 Initializing MigrationEngine...")
    try:
        engine = MigrationEngine(use_v2_parser=True)
        print("✅ MigrationEngine initialized")
    except Exception as e:
        print(f"❌ Error initializing engine: {e}")
        raise
    
    # Generate JSON
    print(f"\n🚀 Generating JSON from TWB file...")
    try:
        result = engine.migrate_file(str(twb_path), output_dir)
        print("✅ JSON generation completed successfully")
        
        # Display summary
        output_path = Path(output_dir) / "processed_pipeline_output.json"
        if output_path.exists():
            print(f"\n📊 Generated JSON file: {output_path}")
            print(f"   File size: {output_path.stat().st_size / 1024:.2f} KB")
        
        return result
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error generating JSON: {error_msg}")
        
        # Check for common validation errors and provide helpful messages
        if "RangeParameterSettings" in error_msg and "max" in error_msg:
            print("   ⚠️  Warning: Parameter range validation error (missing max value)")
            print("   This is a known issue with some Tableau workbooks.")
        elif "NoneType" in error_msg and "lower" in error_msg:
            print("   ⚠️  Warning: Missing aggregation type in measure")
            print("   This is a known issue with some Tableau workbooks.")
        
        import traceback
        traceback.print_exc()
        raise


def process_local_twb_files(twb_files: list, output_dir: str = "output", generate_json: bool = False) -> dict:
    """
    Process multiple local TWB files and optionally generate JSON.
    
    Args:
        twb_files: List of paths to .twb or .twbx files
        output_dir: Directory to save outputs
        generate_json: Whether to generate JSON using MigrationEngine
        
    Returns:
        dict: Processing statistics
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    results = {
        "total_files": len(twb_files),
        "processed": 0,
        "failed": 0,
        "json_files": [],
        "errors": []
    }
    
    print(f"\n{'='*60}")
    print(f"Processing {len(twb_files)} local TWB file(s)")
    print(f"{'='*60}\n")
    
    for i, twb_file in enumerate(twb_files, 1):
        twb_path = Path(twb_file)
        print(f"\n[{i}/{len(twb_files)}] Processing: {twb_path.name}")
        
        try:
            if generate_json:
                # Generate JSON for each file
                file_output_dir = output_path / twb_path.stem
                json_result = generate_json_from_twb(str(twb_path), str(file_output_dir))
                results["json_files"].append(str(file_output_dir / "processed_pipeline_output.json"))
                results["processed"] += 1
                print(f"✅ Successfully processed: {twb_path.name}")
            else:
                # Just validate the file exists
                if twb_path.exists():
                    results["processed"] += 1
                    print(f"✅ File validated: {twb_path.name}")
                else:
                    raise FileNotFoundError(f"File not found: {twb_path}")
                    
        except Exception as e:
            results["failed"] += 1
            error_msg = f"Error processing {twb_path.name}: {str(e)}"
            results["errors"].append(error_msg)
            print(f"❌ {error_msg}")
    
    print(f"\n{'='*60}")
    print(f"Processing complete!")
    print(f"  Total: {results['total_files']}")
    print(f"  Processed: {results['processed']}")
    print(f"  Failed: {results['failed']}")
    if results["json_files"]:
        print(f"  JSON files generated: {len(results['json_files'])}")
    if results["errors"]:
        print(f"\nErrors:")
        for error in results["errors"]:
            print(f"  - {error}")
    print(f"{'='*60}")
    
    return results


def download_workbook_with_retry(server, workbook, file_path, max_retries=3, retry_delay=2):
    """
    Download a workbook with retry logic for connection errors.
    
    Args:
        server: TSC Server instance
        workbook: Workbook object to download
        file_path: Path where to save the workbook
        max_retries: Maximum number of retry attempts
        retry_delay: Initial delay between retries (seconds)
        
    Returns:
        str: Path to downloaded file, or None if all retries failed
    """
    for attempt in range(max_retries):
        try:
            download_path = server.workbooks.download(workbook.id, filepath=str(file_path))
            if Path(download_path).exists() and Path(download_path).stat().st_size > 0:
                return download_path
            else:
                # File doesn't exist or is empty, retry
                if Path(download_path).exists():
                    Path(download_path).unlink()  # Delete empty file
        except Exception as e:
            error_msg = str(e)
            is_connection_error = any(keyword in error_msg.lower() for keyword in [
                'connection broken', 'incompleteread', 'response ended prematurely',
                'timeout', 'connection', 'network'
            ])
            
            if is_connection_error and attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                print(f"    Retry {attempt + 1}/{max_retries} after {wait_time}s...")
                time.sleep(wait_time)
                continue
            else:
                raise e
    
    return None


def process_workbook(server, workbook, batch_folder, split_batch_folder, batch_index, workbook_index):
    """
    Process a single workbook: download, extract XML, and split by dashboard.
    
    Args:
        server: TSC Server instance
        workbook: Workbook object
        batch_folder: Folder to save downloaded workbook
        split_batch_folder: Folder to save split dashboards
        batch_index: Batch number
        workbook_index: Index of workbook in batch
        
    Returns:
        dict: Processing result with status and dashboard count
    """
    safe_name = slugify(workbook.name)
    # Don't include extension - server.workbooks.download() will add .twbx automatically
    file_path = batch_folder / f"{safe_name}_{workbook_index}"
    
    try:
        # Download workbook with retry
        download_path = download_workbook_with_retry(server, workbook, file_path, max_retries=3)
        
        if not download_path or not Path(download_path).exists():
            return {"status": "failed", "name": workbook.name, "error": "Download failed after retries", "dashboards": 0}
        
        # Extract XML from downloaded file
        xml_text = extract_twb_xml(download_path)
        
        if xml_text:
            # Split workbooks by dashboard and save to split_dir
            dash_map = get_dashboard_xml(xml_text)
            
            for dashboard_name, dashboard_xml in dash_map.items():
                dash_file = split_batch_folder / f"{safe_name}_{workbook_index}__{slugify(dashboard_name)}.twb"
                with open(dash_file, "w", encoding="utf-8") as f:
                    f.write(dashboard_xml)
            
            return {"status": "success", "name": workbook.name, "dashboards": len(dash_map)}
        else:
            return {"status": "warning", "name": workbook.name, "error": "Could not extract XML", "dashboards": 0}
            
    except Exception as ex:
        return {"status": "error", "name": workbook.name, "error": str(ex), "dashboards": 0}


def download_workbooks_from_server(
    batch_size=10,
    temp_dir=None,
    split_dir=None,
    project_name=None,
    max_workers=5,
    generate_json=False,
    json_output_dir=None
):
    """
    Download all workbooks from Tableau server and split them by dashboard.
    
    Args:
        batch_size: Number of workbooks to process in each batch (default: 10)
        temp_dir: Directory to store downloaded workbooks (default: "temp_tableau_workbooks")
        split_dir: Directory to store split dashboard files (default: temp_dir/split_workbooks)
        project_name: Optional project name filter (None = all workbooks)
        max_workers: Number of concurrent downloads (default: 5)
        generate_json: Whether to generate JSON from downloaded workbooks (default: False)
        json_output_dir: Directory to save JSON files (default: output)
        
    Returns:
        dict: Dictionary with download statistics
    """
    # Load environment variables directly from .env file (bypasses system env vars)
    env_path = Path(".env")
    print(f"Looking for .env file at: {env_path.absolute()}")
    print(f".env file exists: {env_path.exists()}")
    
    # Read directly from .env file to avoid system variable conflicts
    env_vars = dotenv_values(env_path)
    
    TABLEAU_SERVER_URL = env_vars.get("TABLEAU_SERVER_URL")
    USERNAME = env_vars.get("USERNAME") or env_vars.get("TABLEAU_USERNAME")
    PASSWORD = env_vars.get("PASSWORD") or env_vars.get("TABLEAU_PASSWORD")
    SITE_ID = env_vars.get("SITE_ID") or env_vars.get("TABLEAU_SITE_ID")
    
    # Debug: Print what was loaded (mask password)
    print(f"\nLoaded environment variables:")
    print(f"  TABLEAU_SERVER_URL: {TABLEAU_SERVER_URL}")
    print(f"  USERNAME: {USERNAME}")
    print(f"  PASSWORD: {'***' if PASSWORD else 'NOT SET'}")
    print(f"  SITE_ID: {SITE_ID}")
    
    # Validate required variables
    if not TABLEAU_SERVER_URL:
        raise ValueError("TABLEAU_SERVER_URL is not set in .env file")
    if not USERNAME:
        raise ValueError("TABLEAU_USERNAME is not set in .env file")
    if not PASSWORD:
        raise ValueError("TABLEAU_PASSWORD is not set in .env file")
    
    # Set up directories
    if temp_dir is None:
        temp_dir = Path("temp_tableau_workbooks")
    else:
        temp_dir = Path(temp_dir)
    
    temp_dir.mkdir(exist_ok=True)
    
    if split_dir is None:
        split_dir = temp_dir / "split_workbooks"
    else:
        split_dir = Path(split_dir)
    
    split_dir.mkdir(exist_ok=True)
    
    # Configure server with retry strategy
    server = TSC.Server(TABLEAU_SERVER_URL, use_server_version=True)
    
    # Configure session with retry strategy for connection errors
    session = server._session
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Authenticate with Tableau server
    tableau_auth = TSC.TableauAuth(USERNAME, PASSWORD, site_id=SITE_ID)
    
    total_workbooks = 0
    total_dashboards = 0
    batch_folders = []
    failed_workbooks = []
    
    with server.auth.sign_in(tableau_auth):
        # Get all workbooks across the site
        all_workbooks = []
        req_option = TSC.RequestOptions(pagesize=1000)  # max allowed per page
        page, pagination_item = server.workbooks.get(req_option)
        all_workbooks.extend(page)

        # Loop through additional pages if needed
        while pagination_item.page_number < (
            pagination_item.total_available // pagination_item.page_size + 1
        ):
            req_option.page_number += 1
            page, pagination_item = server.workbooks.get(req_option)
            all_workbooks.extend(page)

        # Filter by project if specified
        if project_name:
            filtered_workbooks = [wb for wb in all_workbooks if wb.project_name == project_name]
        else:
            filtered_workbooks = all_workbooks
        
        total_workbooks = len(filtered_workbooks)
        print(f"Found {total_workbooks} workbooks to download")
        print(f"Using {max_workers} concurrent workers for faster downloads\n")

        # Process workbooks in batches
        for batch_index in range(0, len(filtered_workbooks), batch_size):
            batch_workbooks = filtered_workbooks[batch_index:batch_index + batch_size]
            batch_number = (batch_index // batch_size) + 1
            
            batch_folder = temp_dir / f"batch_{batch_number}"
            batch_folder.mkdir(parents=True, exist_ok=True)
            batch_folders.append(batch_folder)
            
            split_batch_folder = split_dir / f"batch_{batch_number}"
            split_batch_folder.mkdir(parents=True, exist_ok=True)

            print(f"Processing batch {batch_number} ({len(batch_workbooks)} workbooks)...")

            # Process workbooks concurrently
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all workbooks in the batch
                future_to_workbook = {
                    executor.submit(
                        process_workbook,
                        server, workbook, batch_folder, split_batch_folder,
                        batch_number, i
                    ): workbook
                    for i, workbook in enumerate(batch_workbooks)
                }
                
                # Process completed downloads as they finish
                for future in as_completed(future_to_workbook):
                    workbook = future_to_workbook[future]
                    try:
                        result = future.result()
                        if result["status"] == "success":
                            print(f"  ✓ {result['name']}: {result['dashboards']} dashboard(s)")
                            total_dashboards += result["dashboards"]
                        elif result["status"] == "warning":
                            print(f"  ⚠ {result['name']}: {result.get('error', 'No dashboards found')}")
                        else:
                            print(f"  ✗ {result['name']}: {result.get('error', 'Failed')}")
                            failed_workbooks.append(result["name"])
                    except Exception as ex:
                        print(f"  ✗ {workbook.name}: Exception - {ex}")
                        failed_workbooks.append(workbook.name)
    
    print(f"\n{'='*60}")
    print(f"Download complete!")
    print(f"  Total workbooks: {total_workbooks}")
    print(f"  Successfully processed: {total_workbooks - len(failed_workbooks)}")
    print(f"  Failed: {len(failed_workbooks)}")
    print(f"  Total dashboards: {total_dashboards}")
    print(f"  Workbooks saved to: {temp_dir}")
    print(f"  Dashboards saved to: {split_dir}")
    if failed_workbooks:
        print(f"\nFailed workbooks: {', '.join(failed_workbooks)}")
    print(f"{'='*60}")
    
    json_files = []
    if generate_json:
        print(f"\n{'='*60}")
        print(f"Generating JSON from downloaded workbooks...")
        print(f"{'='*60}")
        
        if json_output_dir is None:
            json_output_dir = Path("output")
        else:
            json_output_dir = Path(json_output_dir)
        
        json_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Find all downloaded .twbx files
        downloaded_files = []
        for batch_folder in batch_folders:
            downloaded_files.extend(list(batch_folder.glob("*.twbx")))
            downloaded_files.extend(list(batch_folder.glob("*.twb")))
        
        print(f"Found {len(downloaded_files)} downloaded workbook(s) to process")
        
        for i, twb_file in enumerate(downloaded_files, 1):
            print(f"\n[{i}/{len(downloaded_files)}] Generating JSON from: {twb_file.name}")
            try:
                # Remove double extension if present (e.g., .twbx.twbx -> .twbx)
                file_stem = twb_file.stem
                if file_stem.endswith('.twbx') or file_stem.endswith('.twb'):
                    # Already has extension in stem, use it as is
                    file_output_dir = json_output_dir / file_stem
                else:
                    # Use the stem normally
                    file_output_dir = json_output_dir / twb_file.stem
                
                generate_json_from_twb(str(twb_file), str(file_output_dir))
                json_files.append(str(file_output_dir / "processed_pipeline_output.json"))
            except Exception as e:
                print(f"❌ Error generating JSON for {twb_file.name}: {e}")
                import traceback
                traceback.print_exc()
                # Continue with next file instead of stopping
        
        print(f"\n✅ JSON generation complete!")
        print(f"  Generated {len(json_files)} JSON file(s)")
        print(f"  Output directory: {json_output_dir}")
    
    return {
        "total_workbooks": total_workbooks,
        "total_dashboards": total_dashboards,
        "batch_folders": batch_folders,
        "temp_dir": temp_dir,
        "split_dir": split_dir,
        "failed_workbooks": failed_workbooks,
        "json_files": json_files if generate_json else []
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Download Tableau workbooks from server OR process local TWB files and generate JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download from server and generate JSON
  python download_and_extract.py --server --generate-json
  
  # Process local TWB files
  python download_and_extract.py --local files/workbook1.twb files/workbook2.twb
  
  # Process local TWB files with custom output directory
  python download_and_extract.py --local files/*.twb --output-dir my_output
        """
    )
    
    # Mode selection
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--server",
        action="store_true",
        help="Download workbooks from Tableau server"
    )
    mode_group.add_argument(
        "--local",
        nargs="+",
        metavar="FILE",
        help="Process local TWB/TWBX files (provide one or more file paths)"
    )
    
    # Server-specific options
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of workbooks per batch when downloading from server (default: 10)"
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=5,
        help="Number of concurrent downloads (default: 5)"
    )
    parser.add_argument(
        "--project-name",
        type=str,
        help="Filter workbooks by project name (server mode only)"
    )
    
    # JSON generation options
    parser.add_argument(
        "--generate-json",
        action="store_true",
        help="Generate JSON output using MigrationEngine"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output",
        help="Directory to save JSON output (default: output)"
    )
    
    args = parser.parse_args()
    
    if args.server:
        # Download from server mode
        print("="*60)
        print("MODE: Download from Tableau Server")
        print("="*60)
        result = download_workbooks_from_server(
            batch_size=args.batch_size,
            max_workers=args.max_workers,
            project_name=args.project_name,
            generate_json=args.generate_json,
            json_output_dir=args.output_dir
        )
        print(f"\n📊 Final Statistics:")
        print(f"  Workbooks: {result['total_workbooks']}")
        print(f"  Dashboards: {result['total_dashboards']}")
        if args.generate_json:
            print(f"  JSON files: {len(result.get('json_files', []))}")
    
    elif args.local:
        # Process local files mode
        print("="*60)
        print("MODE: Process Local TWB Files")
        print("="*60)
        result = process_local_twb_files(
            twb_files=args.local,
            output_dir=args.output_dir,
            generate_json=args.generate_json
        )
        print(f"\n📊 Final Statistics:")
        print(f"  Processed: {result['processed']}")
        print(f"  Failed: {result['failed']}")
        if args.generate_json:
            print(f"  JSON files: {len(result.get('json_files', []))}")

