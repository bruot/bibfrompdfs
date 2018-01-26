#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of the bibfrompdfs software, a script that generates a
# a BibTeX database from PDFs in a folder by following their DOI link.
#
# Copyright 2017 Nicolas Bruot (https://www.bruot.org/hp/)
#
#
# bibfrompdfs is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# bibfrompdfs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with bibfrompdfs.  If not, see <http://www.gnu.org/licenses/>.


"""Browses a directory of PDF files to extract DOI links and build a BibTeX database"""


from __future__ import unicode_literals

import os
import re
import codecs
import argparse
import sys
if sys.version_info[0] < 3:
    from urllib2 import Request, urlopen, HTTPError
else:
    from urllib.request import Request, urlopen, HTTPError
import textract


def get_bib(doi):
    """Returns the BibTeX string for the given DOI"""

    url = 'https://dx.doi.org/%s' % doi
    print(url)
    request = Request(url,
                      headers={'Accept': 'text/bibliography; style=bibtex'})
    response = urlopen(request)
    try:
        encoding = response.headers.get_content_charset()
    except AttributeError:
        encoding = 'utf-8'
    if encoding is None:
        encoding = 'utf-8'
    return response.read().decode(encoding)


def process_pdf(pdf_path, bib_file, first_only=False):
    """Finds DOI in the given PDF file and writes BibTeX data to the output file

    Returns a status in the form ['pdf_status', ['doi_1_status, ...]].
    """

    print(pdf_path)
    doi_status = []
    try:
        text = textract.process(pdf_path)
        if sys.version_info[0] > 2:
            text = str(text)
    except (UnicodeDecodeError, TypeError,
            textract.exceptions.ShellError) as e:
        print('\tError: %s' % e)
        return ['err_parsing', doi_status]

    if len(text) < 200:
        print('\tWarning: Suspiciously short text.')
    pattern = re.compile(r'\d{2}\.\d{4}/[a-z0-9/.()\-]+', re.IGNORECASE)
    matches = re.findall(pattern, text)
    if len(matches) == 0:
        print('\tWarning: No matches.')
        return ['warn_nodata', doi_status]
    if first_only and len(set(matches)) > 1:
        print('\tWarning: Multiple DOIs found (see below); taking the first one.')
        for doi in set(matches):
            print('\t\t%s' % doi)
        dois = [matches[0]]
    else:
        dois = set(matches)
    for doi in dois:
        try:
            bib_text = get_bib(doi)
        except HTTPError as e:
            # When the DOI could not be fetched, it could be because the text
            # caught by the regexp included undesired parentheses at the end:
            stripped_doi = doi.rstrip('()')
            # or dots...
            stripped_doi = stripped_doi.rstrip('.')
            if stripped_doi == doi:
                print('\tError: %s' % e)
                print('\twhen fetching DOI: %s' % doi)
                doi_status.append('doi_err_fetch')
            else:
                try:
                    bib_text = get_bib(stripped_doi)
                except HTTPError as e:
                    print('\tError: %s' % e)
                    print('\twhen fetching stripped DOI: %s' % stripped_doi)
                    doi_status.append('doi_err_fetch')
                else:
                    bib_file.write('%s\n' % bib_text)
                    doi_status.append('doi_success')
        else:
            bib_file.write('%s\n' % bib_text)
            doi_status.append('doi_success')

    return ['success', doi_status]


def main(first_only):
    bib_path = os.path.join(args.directory, 'out.bib')
    summary = {
           'success': 0,
           'warn_nodata': 0,
           'err_parsing': 0,
           }
    doi_summary = {
            'doi_success': 0,
            'doi_err_fetch': 0,
            }
    with codecs.open(bib_path, 'w', 'utf-8') as bib_file:
        for root, dirs, filenames in os.walk(args.directory):
            for filename in filenames:
                path = os.path.join(root, filename)
                if os.path.splitext(path)[1].lower() == '.pdf':
                    result = process_pdf(path, bib_file, first_only)
                    summary[result[0]] += 1
                    for doi_result in result[1]:
                        doi_summary[doi_result] += 1

    print('')
    print('PDF summary:')
    print('\t%d PDF files processed' % sum(summary.values()))
    print('\t%d successful parsing' % summary['success'])
    print('\t%d PDFs with no DOI data found' % summary['warn_nodata'])
    print('\t%d errors while parsing text' % summary['err_parsing'])
    print('DOI summary:')
    print('\t%d DOIs found' % sum(doi_summary.values()))
    print('\t%d successful fetches' % doi_summary['doi_success'])
    print('\t%d errors while fetching DOI' % doi_summary['doi_err_fetch'])
    print('')
    print('BibTeX output written to %s.' % bib_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', help='directory containing the PDF files')
    parser.add_argument('--first', '-f', action='store_true',
                        help='instead of fetching all DOIs of a PDF, only fetch the first one')
    args = parser.parse_args()
    main(args.first)
