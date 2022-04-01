export default getLanguage(language, languages) {
  language ?
  languages.filter(lang => lang === language ) : 'English'
}