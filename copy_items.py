import json

# Read the file from Downloads
with open(r'C:\Users\leigh\Downloads\JDL Bot\csgo_api_v47.json', 'r', encoding='utf-8-sig') as f:
    download_data = json.load(f)

# Read current workspace file
with open(r'C:\Users\leigh\Documents\GitHub\jdl-web-terminal\csgo_api_v47.json', 'r', encoding='utf-8-sig') as f:
    workspace_data = json.load(f)

# Extract item names from download file (it's a dict with item names as keys)
if isinstance(download_data, dict):
    download_items = list(download_data.keys())
    print(f"Items from Downloads: {len(download_items)}")
    
    # Get current items from workspace
    workspace_items = workspace_data.get('items', [])
    print(f"Items in workspace: {len(workspace_items)}")
    
    # Merge and deduplicate
    all_items = list(set(download_items + workspace_items))
    all_items.sort()
    
    print(f"Total merged items: {len(all_items)}")
    
    # Save merged data to workspace
    merged_data = {"items": all_items}
    with open(r'C:\Users\leigh\Documents\GitHub\jdl-web-terminal\csgo_api_v47.json', 'w', encoding='utf-8-sig') as f:
        json.dump(merged_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Successfully merged and saved!")
    print(f"\nFirst 5 items:")
    for i, item in enumerate(all_items[:5], 1):
        print(f"  {i}. {item}")
else:
    print("Download file is not in expected format")
