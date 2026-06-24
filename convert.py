#!/usr/bin/env python3
"""Convert PHP template files to plain HTML by inlining partials."""

import os
import re

BASE = "lovelove-downloadable/lovelove"
PARTIALS = os.path.join(BASE, "partials")

# Read all partial files
def read_partial(name):
    path = os.path.join(PARTIALS, name)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""

# Partial contents
PARTIALS_MAP = {
    "head.php": read_partial("head.php"),
    "header.php": read_partial("header.php"),
    "header-two.php": read_partial("header-two.php"),
    "header-three.php": read_partial("header-three.php"),
    "footer.php": read_partial("footer.php"),
    "script.php": read_partial("script.php"),
    "preloader.php": read_partial("preloader.php"),
    "page-header.php": read_partial("page-header.php"),
    "blog-card.php": read_partial("blog-card.php"),
    "blog-sidebar.php": read_partial("blog-sidebar.php"),
}

def resolve_php_vars(content, php_vars):
    """Replace simple PHP echo statements with their values."""
    # Replace <?php echo $var; ?> and <?= $var ?>
    def replacer(m):
        var = m.group(1).strip().lstrip('$')
        return php_vars.get(var, "")
    content = re.sub(r'<\?(?:php\s+)?echo\s+\$(\w+)\s*;?\s*\?>', replacer, content)
    content = re.sub(r'<\?=\s*\$(\w+)\s*\?>', replacer, content)
    # Remove remaining simple <?php echo (isset($css) ? $css : '') ?> style
    content = re.sub(r'<\?php echo \(isset\(\$\w+\) \? \$\w+\s*: \'\'\)\?>', '', content)
    return content

def extract_php_vars(content):
    """Extract simple $var = 'value'; assignments from PHP blocks."""
    vars_found = {}
    # Match: $VarName = 'some value';
    for m in re.finditer(r"\$(\w+)\s*=\s*['\"]([^'\"]*)['\"];", content):
        vars_found[m.group(1)] = m.group(2)
    return vars_found

def inline_page_header(content, php_vars):
    """Handle page-header partial with variable substitution."""
    partial = PARTIALS_MAP["page-header.php"]
    # Replace php conditionals and variables
    # Remove <?php if (!empty($mainTitle)) : ?> ... <?php endif; ?>
    def replace_if_block(match):
        var = match.group(1)
        inner = match.group(2)
        val = php_vars.get(var, "")
        if val:
            # Remove the <?php echo $var; ?> inside
            inner = re.sub(r'<\?php echo \$' + var + r'; \?>', val, inner)
            return inner
        return ""
    partial = re.sub(
        r'<\?php if \(!empty\(\$(\w+)\)\) : \?>(.*?)<\?php endif; \?>',
        replace_if_block, partial, flags=re.DOTALL
    )
    # Clean remaining PHP tags
    partial = re.sub(r'<\?php[^?]*\?>', '', partial)
    return partial

def process_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract PHP variable assignments
    php_vars = extract_php_vars(content)

    # Handle include statements - replace each include with the partial content
    def replace_include(m):
        partial_name = m.group(1).replace("./partials/", "").replace("'", "").replace('"', '').strip()
        if partial_name == "page-header.php":
            return inline_page_header(content, php_vars)
        partial_content = PARTIALS_MAP.get(partial_name, f"<!-- {partial_name} not found -->")
        # Resolve $HeaderStyle variable in header partials
        if "header" in partial_name:
            partial_content = partial_content.replace(
                '<?php echo $HeaderStyle; ?>', php_vars.get("HeaderStyle", "")
            )
        # Remove leftover PHP echo tags in partials
        partial_content = re.sub(r'<\?php echo \(isset\(\$\w+\) \? \$\w+\s*: \'\'\)\?>', '', partial_content)
        partial_content = re.sub(r'<\?php[^?]*\?>', '', partial_content)
        return partial_content

    # Replace include calls
    content = re.sub(
        r"<\?php include ['\"]([^'\"]+)['\"] \?>",
        replace_include, content
    )
    content = re.sub(
        r"<\?php include\('[^']+'\); \?>",
        replace_include, content
    )

    # Remove remaining PHP blocks (<?php ... ?> and <?= ... ?>)
    content = re.sub(r'<\?php.*?\?>', '', content, flags=re.DOTALL)
    content = re.sub(r'<\?=.*?\?>', '', content, flags=re.DOTALL)

    # Rename .php links to .html
    content = re.sub(r'(href|src)="([^"]*?)\.php([^"]*?)"', 
                     lambda m: f'{m.group(1)}="{m.group(2)}.html{m.group(3)}"', content)

    return content

# Get all .php files in the base directory (not partials)
php_files = [f for f in os.listdir(BASE) if f.endswith(".php")]

converted = 0
for filename in php_files:
    filepath = os.path.join(BASE, filename)
    html_filename = filename.replace(".php", ".html")
    html_filepath = os.path.join(BASE, html_filename)

    try:
        result = process_file(filepath)
        with open(html_filepath, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"✓ {filename} → {html_filename}")
        converted += 1
    except Exception as e:
        print(f"✗ {filename}: {e}")

print(f"\nDone: {converted}/{len(php_files)} files converted.")
