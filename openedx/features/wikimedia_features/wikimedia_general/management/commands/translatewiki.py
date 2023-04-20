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
from polib import pofile, POFile, POEntry

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

    def reset_pofile(self, file_path, output_file):
        """
        """
        _, poids = self._get_msgids_from_po_file(file_path)
        pomsgs = pofile(output_file)
        for entry in pomsgs:
            if entry.msgid in poids:
                entry.msgstr = ""
        pomsgs.save()

    def pull_translation_from_transifex(self, locales, base_lang='en'):
        """
        Pull latest translations from Transifex
        Arguments:
            locales: (list) list of languages i.e ['ar', 'en', 'fr']
        """
        log.info('Pulling Reviewed Translations from Transifex')
        locales = list(set(locales) - set([base_lang]))
        langs = ','.join(locales)
        execute(f'tx pull -f --mode=onlytranslated -l {langs}')

    def get_line_number_from_output(self, output):
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
    
    def _get_paragraph(self, line_numbers, paragraphs):
        fuzzy_paragraphs = []
        for line_number in  line_numbers:
            for start_line, paragraph in paragraphs:
                if start_line <= line_number <= start_line + paragraph.count('\n'):
                    fuzzy_paragraphs.append(paragraph.strip())
        return fuzzy_paragraphs

    def get_paragraphs_from_lines(self, file_path, line_numbers):
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
            
            fuzzy_paragraphs = self._get_paragraph(line_numbers, paragraphs)
            
            dir_path, file_name = os.path.split(file_path)
            temp_path = os.path.join(dir_path, f'temp-{file_name}')
            with open(temp_path, 'w+') as temp_file:
                temp_file.write("\n\n".join(fuzzy_paragraphs))
            self.reset_pofile(temp_path, file_path)
            execute(f'rm {temp_path}')

    def remove_bad_msgstr(self, filename):
        """
        """
        # cmd = f'msgfmt --check-format {filename}'
        cmd = f'django-admin.py compilemessages'
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # check for errors
        if result.returncode != 0:
            # an error occurred, print the error message
            error_msg = result.stderr.decode('utf-8')
            files_mapping = self.get_line_number_from_output(error_msg)
            import pdb; pdb.set_trace();
            for file_path, line_numbers in files_mapping.items():
                self.get_paragraphs_from_lines(file_path, line_numbers)
        else:
            # no error, print the command output
            print(result.stdout.decode('utf-8'))


    def msgmerge(self, locales, translation_files, base_lang='en', generate_po_file_if_not_exist=False, output_file_mapping={}):
        """
        Merge base language translations with other languages
        Arguments:
            locales: (list) list of languages i.e ['ar', 'en', 'fr']
            staged_files: (list) files to copy i.e ['wiki.po', 'wikijs.po']
            base_lang: (str) base language of edx-platform
            generate_po_file_if_not_exist: (bool) if True and destination path doesn't exist, it will create empty po file
            output_file_mapping: (dict) used to generate metadata when creatring new .po file
        """
        msgcat_command = 'msgcat {to} {source} -o {to}'
        locales = list(set(locales) - set([base_lang]))
        edx_translation_path = self.EDX_TRANSLATION_PATH
        for lang in locales:
            base_path = f'{edx_translation_path}/{lang}/LC_MESSAGES'
            for filename in translation_files:
                from_file = f'{base_path}/wm-{filename}'
                to_file = f'{base_path}/{filename}'
                command = msgcat_command.format(to=to_file, source=from_file)
                execute(command)

    def msgmergeold(self, locales, staged_files, base_lang='en', generate_po_file_if_not_exist=False, output_file_mapping={}):
        """
        Merge base language translations with other languages
        Arguments:
            locales: (list) list of languages i.e ['ar', 'en', 'fr']
            staged_files: (list) files to copy i.e ['wiki.po', 'wikijs.po']
            base_lang: (str) base language of edx-platform
            generate_po_file_if_not_exist: (bool) if True and destination path doesn't exist, it will create empty po file
            output_file_mapping: (dict) used to generate metadata when creatring new .po file
        """
        msgmerge_command = 'msgmerge {to} {source} --update --no-fuzzy-matching'
        locales = list(set(locales) - set([base_lang]))
        edx_translation_path = self.EDX_TRANSLATION_PATH
        from_path = f'{edx_translation_path}/{base_lang}/LC_MESSAGES'
        for lang in locales:
            to_path = f'{edx_translation_path}/{lang}/LC_MESSAGES'
            log.info(f'Merging {base_lang} translations with {lang}')
            for filename in staged_files:
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
                    from_path = f'{edx_dir}/{filename}',
                    to_path = f'{wm_dir}/{filename}'
                )
                execute(command)
            
            self._move_files_from_src_to_dest(
                wm_dir, edx_dir, staged_files, delete_src_dir_if_empty=True
            )
        
        log.info(f'{locales} are updated with Transifex Translations')

    def update_translations_from_schema(self, locals, merge_scheme):
        """
        Merge translations of Translatewiki with Transifex
        """
        pomerge_command = 'pomerge --from {from_path} --to {to_path}'
        edx_translation_path = self.EDX_TRANSLATION_PATH

        for lang in locals:
            edx_dir = f'{edx_translation_path}/{lang}/LC_MESSAGES'
            for source_file, files in merge_scheme.items():
                if os.path.exists(f'{edx_dir}/{source_file}'):
                    for filename in files:
                        log.info(f'Updating {edx_dir}/{filename} from {edx_dir}/{source_file}')
                        command = pomerge_command.format(
                            from_path=f'{edx_dir}/{source_file}',
                            to_path=f'{edx_dir}/{filename}',
                        )
                        execute(command)
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
        self.msgmerge(locales, output_files, generate_po_file_if_not_exist=True, output_file_mapping=files_mapping)
        
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
            self.msgmerge(locales, targated_files)
        elif options['action'] == 'remove_bad_msgstr':
            self.remove_bad_msgstr('conf/locale/ca/LC_MESSAGES/django.po')
        elif options['action'] == 'update_translations':
            self.update_translations_from_transifex(locales, staged_files)
        elif options['action'] == 'generate_custom_strings':
            self.generate_custom_strings(targated_files, locales)
        elif options['action'] == 'update_from_translatewiki':
            scheme = {f'wm-{key}': val for key, val in merge_scheme.items()}
            self.update_translations_from_schema(locales, scheme)
        elif options['action'] == 'update_from_manual':
            scheme = {f'manual.po': staged_files}
            self.update_translations_from_schema(locales, scheme)
