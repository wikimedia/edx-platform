"""
Django admin command to automate localization flow using
Translatewiki and Transifex
"""
import os
import re
import yaml
import shutil
from datetime import datetime
import subprocess

from i18n.execute import execute

from django.core.management.base import BaseCommand
from logging import getLogger
from polib import pofile, POFile

log = getLogger(__name__)


class Command(BaseCommand):
    """
    Localization commands
    """
    help = 'Commad to automate localization via Trarnslatewiki and Transifex'

    EDX_TRANSLATION_PATH = 'conf/locale'

    def add_arguments(self, parser):
        """
        Add --commit argument with default value False
        """
        parser.add_argument(
            'action',
            choices=[
                'pull_transifex_translations',
                'msgmerge',
                'update_translations',
                'generate_custom_strings',
                'update_from_translatewiki',
                'update_from_manual',
                'update_from_version',
                'remove_bad_msgstr',
            ],
            help='Send translations to Edx Database',
        )
        parser.add_argument(
            '-l', '--languages', nargs='+', help='Specify languages', default=[],
        )

    def _validating_files(self, dir, files):
        """
        Check if files exists in the directory
        Arguments:
            dir: (src) directory path
            files: (list) files to check in a directory
        """
        log.info(f'Validating files in {dir}')
        for filename in files:
            file_path = f'{dir}/{filename}'
            if not os.path.exists(dir):
                raise ValueError(f"Tranlatewiki: file doesn't exist: {file_path}")

    def _move_files_from_src_to_dest(self, src_dir, dest_dir, files, delete_src_dir_if_empty=False):
        """
        More files from source directory to destination directory
        Arguments:
            src_dir: (str) source root directory i.e 'conf/locale/LC_MESSAGES/ar'
            dest_dir: (str) destination root directory i.e 'conf/locale/LC_MESSAGES/ar/wm'
            files: (list) files to copy i.e ['wiki.po', 'wikijs.po']
            delete_src_dir_if_empty: (bool) If True, delete source folder if empty
        """
        self._validating_files(src_dir, files)
        if not os.path.exists(dest_dir):
            log.info(f'Creating a directory : {dest_dir}')
            os.mkdir(dest_dir)

        log.info(f'Moving files from {src_dir} to {dest_dir}')
        for filename in files:
            soure_file = f'{src_dir}/{filename}'
            output_file = f'{dest_dir}/{filename}'
            shutil.move(soure_file, output_file)

        if delete_src_dir_if_empty and not len(os.listdir(src_dir)):
            log.info(f'Deleting source directory {src_dir}')
            os.rmdir(src_dir)

    def _get_metadata_from_po_file(self, path):
        """
        Returns metadata of po file
        Argument:
            path: (str) po file path i.e conf/locale/LC_MESSAGES/en/django.po
        """
        try:
            pomsgs = pofile(path)
            return pomsgs.metadata
        except:
            return {}

    def _get_msgids_from_po_file(self, path):
        """
        Extract pomsgs and unique ids from po file
        Argument:
            path: (str) po file path i.e conf/locale/LC_MESSAGES/en/django.po
        """
        pomsgs = pofile(path)
        poids = set([entry.msgid for entry in pomsgs])
        return pomsgs, poids

    def _create_or_update_po_file(self, output_file, po_entries, po_meta_data, add_fuzzy=False):
        """
        Create or update po file from list of PoEntry
        Arguments:
            output_file: (str) output file path i.e 'conf/locale/LC_MESSAGES/en/wm-djangojs.po'
            po_entries: (list) list of POEntry
            po_metadata: (dict) metadata used while creating po file
            add_fuzzy: (bool) If True, add ' ,fuzzy' in header
        """
        if os.path.exists(output_file):
            if po_entries:
                pomsgs = pofile(output_file)
                for entry in po_entries:
                    if not pomsgs.find(entry.msgid):
                        pomsgs.append(entry)
                if pomsgs.metadata.get('PO-Revision-Date'):
                    pomsgs.metadata['PO-Revision-Date'] = str(datetime.now())
                pomsgs.save(output_file)
        else:
            po = POFile()
            date = datetime.now()
            po_meta_files = {
                'POT-Creation-Date': str(date),
                'PO-Revision-Date': str(date),
                'Report-Msgid-Bugs-To': 'Translatewiki',
                'Last-Translator': '',
                'Language-Team': 'Translatewiki',
            }
            po_meta_data.update(po_meta_files)
            po.metadata = po_meta_data
            if add_fuzzy:
                po.header = ', fuzzy'
            for entry in po_entries:
                po.append(entry)
            po.save(output_file)

    def reset_pofile(self, file_path, output_file_path):
        """
        Removes msgstr from pofile
        """
        _, poids = self._get_msgids_from_po_file(file_path)
        pomsgs = pofile(output_file_path)
        for entry in pomsgs:
            if entry.msgid in poids:
                entry.msgstr = ""
                entry.msgstr_plural = {k: "" for k in entry.msgstr_plural}
        pomsgs.save()

    def rename_version_files_and_remove_errors(self, locales):
        """
        Rename version files and remove fuzzy msgstrs
        """
        version_files = ['django.po.new', 'djangojs.po.new']
        edx_translation_path = self.EDX_TRANSLATION_PATH
        for lang in locales:
            for filename in version_files:
                path = f'{edx_translation_path}/{lang}/LC_MESSAGES'
                if os.path.exists(f'{path}/{filename}'):
                    new_filename = f'version-{filename.replace(".new", "")}'
                    execute(f'mv -v {path}/{filename} {path}/{new_filename}')
                    self.remove_bad_msgstr(f'{path}/{new_filename}')

    def process_version_files(self, locales, base_lang='en'):
        """
        Fetch version files from the transifex, remove errors, and rename the files to version-<filename>
        """
        log.info('Updating the confg file')
        execute('mv -v .tx/config .tx/config-edx; mv -v .tx/config-version .tx/config;')

        log.info('Pulling Version Translations from Transifex')
        locales = list(set(locales) - set([base_lang]))
        langs = ','.join(locales)

        execute(f'tx pull --keep-new-files --mode=reviewed -l {langs} -d')
        execute('mv -v .tx/config .tx/config-version; mv -v .tx/config-edx .tx/config;')

        self.rename_version_files_and_remove_errors(locales)

    def pull_translation_from_transifex(self, locales, base_lang='en'):
        """
        Pull latest translations from Transifex
        Arguments:
            locales: (list) list of languages i.e ['ar', 'en', 'fr']
        """
        log.info('Pulling Reviewed Translations from Transifex')
        locales = list(set(locales) - set([base_lang]))
        langs = ','.join(locales)
        execute(f'tx pull --mode=reviewed -l {langs}')
        self.process_version_files(locales, base_lang)

    def _get_line_number_from_output(self, output):
        """
        Extract line number from the error message
        """
        output_mappings = {}
        pattern = r"(conf/locale/)(.+)(:\d+)"

        for output_line in output.split('\n'):
            match = re.search(pattern, output_line)
            if match:
                # Extract the matched substring
                file_name, line_number = match.group(1) + match.group(2), int(match.group(3)[1:])
                if file_name in output_mappings:
                    output_mappings[file_name].append(line_number)
                else:
                    output_mappings[file_name] = [line_number]
        return output_mappings
    
    def _get_line_number_from_validate_output(self, output):
        """ 
        Extracts file paths and line numbers from the given 'output' string,
        specifically targeting paragraphs containing 'fatal error'.

        Parameters:
        - output (str): The string output of i18n_tool validate.

        Returns:
        dict: A dictionary mapping absolute file paths to lists of line numbers.
              Each file path represents sources of 'fatal error' in the 'output'.
        """
        output_mappings = {}
        
        pattern = r"(.+LC_MESSAGES/.+):(\d+)"
        cwd = os.getcwd()

        for paragraph in output.split('\n\n'):
            if 'fatal error' in paragraph:
                match = re.findall(pattern, paragraph)
                if match:
                    file_path_abs = os.path.join(cwd, 'conf', 'locale', match[-1][0])
                    line_number = int(match[-1][1])
                    # store file path and line number
                    if file_path_abs in output_mappings:
                        output_mappings[file_path_abs].append(line_number)
                    else:
                        output_mappings[file_path_abs] = [line_number]

        return output_mappings

    def _get_bad_paragraphs(self, line_numbers, paragraphs):
        """
        Returns paragraphs containing given line_numbers
        """
        fuzzy_paragraphs = []
        for line_number in line_numbers:
            for start_line, paragraph in paragraphs:
                if start_line <= line_number <= start_line + paragraph.count('\n'):
                    fuzzy_paragraphs.append(paragraph.strip())
        return fuzzy_paragraphs

    def get_paragraphs(self, file_path):
        """
        Extract and return message paragraphs from file.

        Parameters:
        - file_path (str): The path to the input po file to extract paragraphs from.

        This function splits the content of the file into paragraphs based on empty lines,
        and returns a list of tuples. Each tuple contains the starting line number and the text of a paragraph.

        Returns:
        - list of tuple: [(start_line_number, paragraph_text),...].

        """
        paragraphs = []

        with open(file_path, 'r') as file:
            # read the contents of the file
            file_contents = file.read()
            current_paragraph = ''
            current_line_number = 1
            for line_number, line in enumerate(file_contents.splitlines()):
                if line.strip() == '':
                    if current_paragraph:
                        paragraphs.append((current_line_number, current_paragraph.strip()))
                        current_paragraph = ''
                    current_line_number = line_number + 2
                else:
                    current_paragraph += line + '\n'
            if current_paragraph:
                paragraphs.append((current_line_number, current_paragraph.strip()))

        return paragraphs

    def _remove_bad_msgstr(self, file_path, line_numbers):
        """
        Remove invalid 'msgstr' entries from a PO file, keeping only valid message paragraphs.

        Parameters:
        - file_path (str): The path to the input PO file to be cleaned.
        - line_numbers (list): A list of line numbers corresponding to invalid translations.

        This function reads the contents of a PO file, splits it into paragraphs based on empty lines,
        and identifies invalid 'msgstr' entries. It then creates a temporary file containing only
        the invalid message paragraphs and resets those entries in the original file.

        Returns:
        - None
        """
        # split file into list of paragraphs
        paragraphs = self.get_paragraphs(file_path)

        fuzzy_paragraphs = self._get_bad_paragraphs(line_numbers, paragraphs)

        # create a temporary file to store fuzzy paragraphs
        dir_path, file_name = os.path.split(file_path)
        temp_path = os.path.join(dir_path, f'temp-{file_name}')
        with open(temp_path, 'w+') as temp_file:
            temp_file.write("\n\n".join(fuzzy_paragraphs))

        self.reset_pofile(temp_path, file_path)
        execute(f'rm {temp_path}')

    def remove_bad_msgstr(self, filename=None):
        """
        Execute commands to check for compile errors and i18n fatal errors, and remove fuzzy msgstr entries.

        Parameters:
        - filename (str, optional): The name of the specific translation file to check.
                                    If not provided, the entire project will be checked.

        Notes:
        - If 'filename' is provided, only the specified file is checked for compile errors.
          If 'filename' is not provided, the entire project is checked, and i18n fatal errors are also checked.
        - If checking the entire project, compile and i18n errors are merged into a combined 'files_mapping'.
        - The method then iterates through each file in 'files_mapping' and removes fuzzy 'msgstr' entries
          based on the identified line numbers.
        """


        compile_error_mapping = self._check_for_compile_errors(filename)
        files_mapping = compile_error_mapping
        
        # if checking all files then include i18n errors 
        if not filename:
            i18n_error_mappinng = self._check_for_i18n_fatal_errors()
            # merge compile and i18n errors
            files_mapping = {
                k: compile_error_mapping.get(k, []) + i18n_error_mappinng.get(k, [])
                for k in set(compile_error_mapping) | set(i18n_error_mappinng)
            }

        for file_path, line_numbers in files_mapping.items():
            self._remove_bad_msgstr(file_path, line_numbers)
    
    def _check_for_compile_errors(self, filename=None):
        """
        Check for compile errors in a Django translation file or project.

        Parameters:
        - filename (str, optional): The name of the specific translation file to check.
                                If not provided, the entire project will be checked.

        Returns:
        dict: A dictionary mapping absolute file paths to lists of line numbers.
              Each entry represents a compilation error found in the specified file or project.

        Notes:
        - If 'filename' is provided, only the specified file is checked; otherwise, the entire project is checked.
        - The function uses 'msgfmt --check-format' for individual files and 'django-admin.py compilemessages'
          for the entire project.
        - Compilation errors are detected in the standard error output of the subprocess.
        - The error messages are further processed to extract file paths and line numbers
          using the '_get_line_number_from_output' method.
        """
        compile_error_mapping = {}

        if filename:
            cmd = f'msgfmt --check-format {filename}'
        else:
            cmd = 'django-admin.py compilemessages'
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            try:
                error_msg = result.stderr.decode('utf-8')
            except UnicodeDecodeError:
                error_msg = result.stderr.decode('latin-1')

            compile_error_mapping = self._get_line_number_from_output(error_msg)

        return compile_error_mapping

    def _check_for_i18n_fatal_errors(self):
        """
        Check for internationalization (i18n) fatal errors using an i18n validation tool.

        Returns:
        dict: A dictionary mapping absolute file paths to lists of line numbers.
              Each entry represents an i18n fatal error found during validation.

        Notes:
        - The method uses the 'i18n_tool validate' command to perform validation.
        - The result is captured from the standard output of the subprocess.
        - The standard output is decoded, and the resulting error message is processed
          to extract file paths and line numbers.
        """

        cmd = 'i18n_tool validate'
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            error_msg = result.stdout.decode('utf-8')
        except UnicodeDecodeError:
            error_msg = result.stdout.decode('latin-1')

        i18n_error_mappinng = self._get_line_number_from_validate_output(error_msg)
        return i18n_error_mappinng


    def msgmerge(self, locales, staged_files, base_lang='en', generate_po_file_if_not_exist=False, output_file_mapping: dict = {}, exclude_files: list = ['wm-django.po', 'wm-djangojs.po', 'manual.po', 'manualjs.po']):
        """
        Merge base language translations with other languages
        Arguments:
            locales: (list) list of languages i.e ['ar', 'en', 'fr']
            staged_files: (list) files to copy i.e ['wiki.po', 'wikijs.po']
            base_lang: (str) base language of edx-platform
            generate_po_file_if_not_exist: (bool) if True and destination path doesn't exist, it will create empty po file
            output_file_mapping: (dict) used to generate metadata when creatring new .po file
            exclude_files: (list) exclude files in the staged_files 
        """
        msgmerge_command = 'msgmerge {to} {source} --update --no-fuzzy-matching'
        locales = list(set(locales) - set([base_lang]))
        edx_translation_path = self.EDX_TRANSLATION_PATH
        from_path = f'{edx_translation_path}/{base_lang}/LC_MESSAGES'
        for lang in locales:
            to_path = f'{edx_translation_path}/{lang}/LC_MESSAGES'
            log.info(f'Merging {base_lang} translations with {lang}')
            for filename in staged_files:
                if filename not in exclude_files:
                    from_file = f'{from_path}/{filename}'
                    to_file = f'{to_path}/{filename}'
                    if generate_po_file_if_not_exist and not os.path.exists(to_file):
                        log.info(f'{to_file} not exist, Creating {filename} in {to_path}')
                        meta_data = self._get_metadata_from_po_file(f'{to_path}/{output_file_mapping[filename]}')
                        self._create_or_update_po_file(to_file, [], meta_data)
                    command = msgmerge_command.format(to=to_file, source=from_file)
                    execute(command)

    def update_translations_from_transifex(self, locales, staged_files, base_lang='en'):
        """
        Merge base language translations with other languages
        Arguments:
            locales: (list) list of languages i.e ['ar', 'en', 'fr']
            staged_files: (list) files to copy i.e ['wiki.po', 'wikijs.po']
            base_lang: (str) base language of edx-platform
        """
        transifex_token = os.getenv('TX_TOKEN')
        if not transifex_token:
            raise ValueError(
                'Translatewiki: Transifex token not found, set TX_TOKEN as an env variable'
            )

        pomerge_command = 'pomerge --from {from_path} --to {to_path}'
        locales = list(set(locales) - set([base_lang]))

        edx_translation_path = self.EDX_TRANSLATION_PATH
        for lang in locales:
            edx_dir = f'{edx_translation_path}/{lang}/LC_MESSAGES'
            wm_dir = f'{edx_translation_path}/{lang}/LC_MESSAGES/wm'

            self._move_files_from_src_to_dest(edx_dir, wm_dir, staged_files)

            log.info(f'Pulling {lang} translations from Transifex')
            execute(f'tx pull --mode=reviewed -l {lang}')

            log.info(f'Merging Transifex {lang} files to platform {lang} files')
            for filename in staged_files:
                command = pomerge_command.format(
                    from_path=f'{edx_dir}/{filename}',
                    to_path=f'{wm_dir}/{filename}'
                )
                execute(command)

            self._move_files_from_src_to_dest(
                wm_dir, edx_dir, staged_files, delete_src_dir_if_empty=True
            )

        log.info(f'{locales} are updated with Transifex Translations')

    def update_translations_from_schema(self, locals, merge_scheme, override=True):
        """
        Merge translations of Translatewiki with Transifex
        """
        pomerge_command = 'pomerge --from {from_path} --to {to_path}'
        if not override:
            pomerge_command = 'pomerge --from {from_path} --to {to_path} --no-overwrite'

        edx_translation_path = self.EDX_TRANSLATION_PATH

        for lang in locals:
            edx_dir = f'{edx_translation_path}/{lang}/LC_MESSAGES'
            for source_file, files in merge_scheme.items():
                if os.path.exists(f'{edx_dir}/{source_file}'):
                    for filename in files:
                        if os.path.exists(f'{edx_dir}/{filename}'):
                            log.info(f'Updating {edx_dir}/{filename} from {edx_dir}/{source_file}')
                            command = pomerge_command.format(
                                from_path=f'{edx_dir}/{source_file}',
                                to_path=f'{edx_dir}/{filename}',
                            )
                            execute(command)
                        else:
                            log.info(f'Unable to find destination path: {edx_dir}/{filename}')
                else:
                    log.info(f'Unable to find source path: {edx_dir}/{source_file}')

    def generate_custom_strings(self, target_files, locales, base_lang='en', prefix='wm'):
        """
        Merge base language translations with other languages
        Arguments:
            target_files: (list) target files i.e ['django.po', 'djangojs.po']
            locales: (list) list of languages i.e ['ar', 'en', 'fr']
            base_lang: (str) base language of edx-platform
            prefix: (str) prefix on new generated files
        """
        transifex_token = os.getenv('TX_TOKEN')
        if not transifex_token:
            raise ValueError('Translatewiki: Transifex token not found, set TX_TOKEN as an env variable')

        edx_translation_path = self.EDX_TRANSLATION_PATH
        locales = list(set(locales) - set([base_lang]))

        edx_dir = f'{edx_translation_path}/{base_lang}/LC_MESSAGES'
        wm_dir = f'{edx_translation_path}/{base_lang}/LC_MESSAGES/wm'

        self._move_files_from_src_to_dest(edx_dir, wm_dir, target_files)

        log.info(f'Pulling {base_lang} translations from Transifex')
        execute(f'tx pull --mode=reviewed -l {base_lang}')
        output_files = []
        for filename in target_files:
            log.info(f'Generating new po file from {edx_dir}/{filename}')
            _, tx_ids = self._get_msgids_from_po_file(f'{edx_dir}/{filename}')
            edx_msgs, edx_ids = self._get_msgids_from_po_file(f'{wm_dir}/{filename}')
            custom_ids = edx_ids - tx_ids
            po_entries = [edx_msgs.find(msgid) for msgid in custom_ids]
            output_file = f'{edx_dir}/{prefix}-{filename}'
            self._create_or_update_po_file(
                output_file, po_entries, edx_msgs.metadata, add_fuzzy=True,
            )
            output_files.append(f'{prefix}-{filename}')

        self._move_files_from_src_to_dest(wm_dir, edx_dir, target_files, delete_src_dir_if_empty=True)
        files_mapping = dict(zip(output_files, target_files))
        self.msgmerge(locales, output_files, generate_po_file_if_not_exist=True, output_file_mapping=files_mapping, exclude_files=[])

        log.info(f'{len(output_files)} new file(s) are created {output_files}')

    def process_configuration_file(self, filepath):
        """
        Process configuration file to get locals and untracked files
        Argument:
            filepath: localization config file i.e conf/locale/config.yaml
        """
        configuration = {}
        with open(filepath, "r") as stream:
            configuration = yaml.safe_load(stream)
        locales = configuration.get('locales')
        merge_scheme = configuration.get('generate_merge')
        staged_files = []
        targated_files = []
        for key, value in merge_scheme.items():
            targated_files.append(key)
            staged_files.extend(value)

        return locales, targated_files, staged_files, merge_scheme

    def handle(self, *args, **options):
        """
        Handle Translatewiki Localization Opeerations
        """
        locales, targated_files, staged_files, merge_scheme = self.process_configuration_file('conf/locale/config.yaml')
        languages = options.get('languages', [])

        if languages:
            if len(set(locales) - set(languages)) == len(set(locales)):
                raise ValueError(f'Invaild Languages, valid languages are {locales}')
            locales = languages

        if options['action'] == 'pull_transifex_translations':
            self.pull_translation_from_transifex(locales)
        elif options['action'] == 'msgmerge':
            self.msgmerge(locales, staged_files)
        elif options['action'] == 'remove_bad_msgstr':
            self.remove_bad_msgstr()
        elif options['action'] == 'update_translations':
            self.update_translations_from_transifex(locales, staged_files)
        elif options['action'] == 'generate_custom_strings':
            self.generate_custom_strings(targated_files, locales)
        elif options['action'] == 'update_from_translatewiki':
            scheme = {f'wm-{key}': val for key, val in merge_scheme.items()}
            self.update_translations_from_schema(locales, scheme)
        elif options['action'] == 'update_from_version':
            scheme = {f'version-{key}': val for key, val in merge_scheme.items()}
            self.update_translations_from_schema(locales, scheme, False)
        elif options['action'] == 'update_from_manual':
            scheme = {'manual.po': staged_files}
            self.update_translations_from_schema(locales, scheme)
