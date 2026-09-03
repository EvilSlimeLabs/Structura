# Translation Guide

This guide explains how to contribute translations for Structura.

## Adding a New Language

To add a new language, follow these steps:

1. **Create a new column in `lookups/langs.csv`.** Use the ISO code of the language as the column header.
2. **Provide translations for all existing keys.** Fill in the new column with the appropriate translations for each string.
3. **Test your translations.** Run Structura and switch to your new language to ensure all labels and messages appear correctly.
4. **Submit a pull request.** Include your updated `langs.csv`.