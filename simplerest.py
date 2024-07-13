from urllib.request import HTTPErrorProcessor, Request, build_opener
from time import gmtime, strftime
import sublime
import sublime_plugin
import hashlib


class NonRaisingHTTPErrorProcessor(HTTPErrorProcessor):
    http_response = https_response = lambda self, request, response: response


class SimplerestRequest(sublime_plugin.TextCommand):
    def headers_to_annotation(self, headers):
        lines = ["<div><i>" + k + "</i>: " + v +
                 "</div>" for k, v in headers.items()]
        return "<body>" + "".join(lines) + "</body>"

    def method_and_url(self, first_line):
        parts = first_line.split(maxsplit=1)
        if len(parts) == 2:
            method = parts[0]
            url = parts[1]
        else:
            method = "GET"
            url = parts[0]
        return method, url

    def split_idx(self, lines):
        for idx, line in enumerate(lines):
            if line.strip() == '':
                return idx
        return None

    def drop_empty_lines(self, lines):
        return [l.strip() for l in lines if l.strip() != '']

    def parse_headers(self, headers_lines):
        lines = self.drop_empty_lines(headers_lines)
        headers = {}
        for l in lines:
            name, value = l.split(':', maxsplit=1)
            headers[name.strip()] = value.strip()
        return headers

    def headers_and_body(self, rest_lines):
        split = self.split_idx(rest_lines)
        headers = []
        body = None
        if split is None:
            headers = self.parse_headers(rest_lines)
        else:
            headers = self.parse_headers(rest_lines[0:split])

            body_lines = self.drop_empty_lines(rest_lines[split:])
            if len(body_lines) > 0:
                body = "\n".join(body_lines).encode('utf-8')

        return headers, body

    def parse_request(self, selected_text):
        lines = selected_text.splitlines()
        method, url = self.method_and_url(lines[0])
        headers, body = self.headers_and_body(lines[1:])
        return Request(url=url, method=method, headers=headers, data=body)

    def run(self, edit):
        view = sublime.active_window().active_view()
        selection = view.sel()
        selectedText = view.substr(selection[0])

        if not selectedText.strip():
            sublime.status_message("Nothing selected")
            return

        request = self.parse_request(selectedText)

        opener = build_opener(NonRaisingHTTPErrorProcessor)
        resp = opener.open(request)
        contents = resp.read().decode("utf-8")
        headers = resp.headers.as_string()
        annotation = self.headers_to_annotation(resp.headers)

        ts = strftime("%Y-%m-%d %H:%M:%S", gmtime())
        result = ">>> " + ts + " >>> " + \
            str(resp.status) + " " + resp.reason + "\n" + contents + "\n"
        mark_scope = "region.greenish"
        if resp.status >= 400:
            mark_scope = "region.redish"
        for region in view.sel():
            if not region.empty():
                view.insert(edit, region.end(), "\n" + result)
                reg = view.find(result, region.end(),
                                sublime.LITERAL)
                key = hashlib.sha256(result.encode()).hexdigest()
                view.add_regions(
                    key=key,
                    regions=[reg],
                    scope=mark_scope,
                    icon="dot",
                    flags=sublime.HIDDEN,
                    annotations=[annotation],
                    annotation_color="grey"
                )
