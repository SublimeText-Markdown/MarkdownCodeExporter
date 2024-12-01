import sublime
import sublime_plugin
import re
import os
from html import escape

class MarkdownCodeExporter(sublime_plugin.ViewEventListener):
    @classmethod
    def is_applicable(cls, settings):
        return settings.get('syntax', '').lower().find('markdown') != -1

    def __init__(self, view):
        super().__init__(view)
        self.phantom_set = sublime.PhantomSet(view)
        self.update_phantoms()

    def on_modified(self):
        # Don't operate on 1MB or larger files.
        if self.view.size() > 2**20:
            return

        self.update_phantoms()

    def on_load(self):
        self.update_phantoms()

    def update_phantoms(self):
        # Find all fenced code blocks
        code_blocks = self.find_code_blocks()
        phantoms = []

        for region in code_blocks:
            # Create phantom content
            content = '''
                <body id="markdown-code-exporter">
                    <style>
                        div {
                            padding: 0.2rem 0;
                            margin-bottom: 3px;
                        }
                        a {
                            padding: 0.4rem;
                            border-radius: 5px;

                            color: #000;
                            background-color: #CCCCCC;

                            text-decoration: none;
                        }
                    </style>
                    <div>
                        <a href="copy">copy</a>
                        <a href="new_tab">open in tab</a>
                    </div>
                </body>
            '''

            # Create and add phantom
            phantom = sublime.Phantom(
                sublime.Region(region.begin() - 1, region.begin() - 1), # -1 puts the phantom to the previous line.
                content,
                sublime.LAYOUT_BLOCK,
                on_navigate=lambda href, region=region: self.handle_phantom_click(href, region)
            )
            phantoms.append(phantom)

        self.phantom_set.update(phantoms)

    def find_code_blocks(self):
        code_blocks = []
        view = self.view

        # Find all fenced code blocks (```)
        content = view.substr(sublime.Region(0, view.size()))
        pattern = r'^( *```+)[\w\-]*\n[\s\S]*?\n\1$'
        matches = re.finditer(pattern, content, re.MULTILINE)

        for match in matches:
            start = match.start()
            end = match.end()
            code_blocks.append(sublime.Region(start, end))

        return code_blocks

    def handle_phantom_click(self, href, region):
        # Get the code content (excluding the first and last lines with ```)
        lines = self.view.substr(region).split('\n')
        code = '\n'.join(lines[1:-1]) + "\n"

        if href == "copy":
            # Copy to clipboard
            sublime.set_clipboard(code)
            sublime.status_message("Code copied to clipboard")

        elif href == "new_tab":
            # Open in new tab
            new_view = self.view.window().new_file()
            new_view.run_command('append', {'characters': code})

            # Try to detect and set syntax
            identifier = re.sub(r"^ *`+", "", lines[0]).strip().lower()  # Remove ``` and get language identifier

            # We want to prevent mismatches. For example, "sql" might match with
            # "Packages/Rails/SQL (Rails).sublime-syntax" before it matches with
            # "Packages/SQL/SQL.sublime-syntax".
            #
            # There may be syntaxes here that Sublime Text doesn't have. Those will
            # be skipped and the first existing syntax will be used.
            id_syntax_map = [
                {
                    "identifier": ["md", "markdown", "mdown"],
                    "syntaxes": [
                        "Packages/MarkdownEditing/Markdown.sublime-syntax",
                        "Packages/MarkdownEditing/MultiMarkdown.tmLanguage",
                        "Packages/MarkdownEditing/Markdown (Standard).tmLanguage",
                        "Packages/Markdown/Markdown.sublime-syntax",
                        "Packages/Markdown/MultiMarkdown.sublime-syntax",
                    ],
                },
                {
                    "identifier": ["js", "javascript"],
                    "syntaxes": [
                        "Packages/JavaScript/JavaScript.sublime-syntax",
                    ],
                },
                {
                    "identifier": ["html"],
                    "syntaxes": [
                        "Packages/HTML/HTML.sublime-syntax",
                    ],
                },
                {
                    "identifier": ["java"],
                    "syntaxes": [
                        "Packages/Java/Java.sublime-syntax",
                    ],
                },
                {
                    "identifier": ["php"],
                    "syntaxes": [
                        "Packages/PHP/PHP.sublime-syntax",
                    ],
                },
                {
                    "identifier": ["py", "python"],
                    "syntaxes": [
                        "Packages/Python/Python.sublime-syntax",
                    ],
                },
                {
                    "identifier": ["rb", "ruby"],
                    "syntaxes": [
                        "Packages/Ruby/Ruby.sublime-syntax",
                    ],
                },
                {
                    "identifier": ["sh", "shell"],
                    "syntaxes": [
                        "Packages/ShellScript/Shell-Unix-Generic.sublime-syntax",
                    ],
                },
                {
                    "identifier": ["sql"],
                    "syntaxes": [
                        "Packages/SQL/SQL.sublime-syntax",
                    ],
                },
            ]

            if not identifier:
                return

            syntax_files = sublime.find_resources('*.tmLanguage') + sublime.find_resources('*.sublime-syntax')

            for mapping in id_syntax_map:
                if not identifier in mapping["identifier"]:
                    continue

                # Now find the first syntax that Sublime Text supports.
                for syntax in mapping["syntaxes"]:
                    if syntax in syntax_files:
                        new_view.assign_syntax(syntax)
                        return

            # There were no match with "id_syntax_map". Now do a plain search.

            for syntax_file in syntax_files:
                if identifier in os.path.basename(syntax_file.lower()):
                    new_view.assign_syntax(syntax_file)
                    return
