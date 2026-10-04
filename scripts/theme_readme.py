import re

def main():
    path = r"b:\Desktop\BASSD\BELCO\AAS-T_AISD\zFAL26\MNIME\README.md"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Extract the Project Architecture block
    match = re.search(r'## Project Architecture\n\n```\n(.*?)```', content, re.DOTALL)
    if not match:
        print("Could not find the architecture block!")
        return
        
    tree = match.group(1)
    
    # Inject fusion_engine.py
    tree = tree.replace(
        "    ├── file_item.py       # Data model & thumbnail caching\n",
        "    ├── file_item.py       # Data model & thumbnail caching\n    ├── fusion_engine.py     # Neural Assimilation Engine (Weight Fusion)\n"
    )
    
    # HTML-ify the tree
    html_lines = ["<pre><code>"]
    
    for line in tree.split("\n"):
        if not line.strip():
            continue
            
        # Separate the comment from the file/folder
        parts = line.split("#", 1)
        main_part = parts[0]
        comment_part = f" <font color='#888888'>#{parts[1]}</font>" if len(parts) > 1 else ""
        
        # Colorize folders (ending with /)
        if "/" in main_part and "MNIME/" not in main_part:
            # find the folder name
            m = re.search(r'([a-zA-Z0-9_.-]+/)\s*$', main_part)
            if m:
                folder = m.group(1)
                main_part = main_part.replace(folder, f"<font color='#00e5ff'><b>{folder}</b></font>")
        elif "MNIME/" in main_part:
            main_part = main_part.replace("MNIME/", "<font color='#00e5ff'><b>MNIME/</b></font>")
        else:
            # It's a file. 
            m = re.search(r'([a-zA-Z0-9_.-]+\.[a-zA-Z0-9]+)\s*$', main_part)
            if m:
                filename = m.group(1)
                if filename.endswith(".py"):
                    color = "#39ff14"
                elif filename.endswith(".pdf") or filename.endswith(".png") or filename.endswith(".gif") or filename.endswith(".jpg"):
                    color = "#ff00ff"
                else:
                    color = "#ffd700"
                main_part = main_part.replace(filename, f"<font color='{color}'>{filename}</font>")
                
        # Handle the tree unicode characters to ensure they render perfectly in HTML
        # The user has weird encoding chars like \x95\x9f\x94\x94. Let's just fix them if needed.
        # It's better to replace them with standard box drawing:
        # Actually I'll leave them as is, just escape HTML
        main_part = main_part.replace("<font", "%%%FONT%%%").replace("</font>", "%%%ENDFONT%%%").replace("<b>", "%%%B%%%").replace("</b>", "%%%ENDB%%%")
        main_part = html.escape(main_part)
        main_part = main_part.replace("%%%FONT%%%", "<font").replace("%%%ENDFONT%%%", "</font>").replace("%%%B%%%", "<b>").replace("%%%ENDB%%%", "</b>")
        
        html_lines.append(main_part + comment_part)
        
    html_lines.append("</code></pre>")
    
    html_tree = "\n".join(html_lines)
    
    # We will replace the ``` block with the HTML block
    new_content = content[:match.start()] + "## Project Architecture\n\n" + html_tree + "\n" + content[match.end():]
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)
        
    print("Successfully themed the architecture tree in README.md!")

if __name__ == "__main__":
    import html
    main()
