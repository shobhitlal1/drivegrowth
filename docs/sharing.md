# Sharing and running DriveGrowth

The source ZIP contains the application, SQL, tests, requirements, documentation and screenshots. It intentionally excludes the Python environment, caches, generated datasets, local databases and private configuration.

## Review in ChatGPT

Attach `DriveGrowth-source.zip` to a conversation using the file attachment button. For example:

> Review this synthetic insurance marketplace analytics project for a Business Operations / Product Analytics portfolio. Start with README.md, docs/experimentation.md and docs/experiment_review.md. Assess the decision logic, statistics, SQL, financial assumptions and user experience. Do not invent real-company results.

The screenshots and generated decision summaries can be reviewed immediately. Running the application or all tests requires regenerating the excluded data first, using the commands in the main README.

## Use the GitHub repository

GitHub stores the individual source files and their change history. The ZIP is useful for sharing with ChatGPT; it is not a substitute for uploading the extracted source files into the repository.

The repository README appears on its home page. Its screenshots and documentation links work directly on GitHub. Source publication does not host the live Streamlit application; the local app still runs separately.

For future changes, ask Codex to review and publish the current DriveGrowth changes. The `.gitignore` file excludes generated data, environments, local databases and common secret files. Review the files being uploaded whenever you introduce new configuration or external integrations.

The project contains synthetic data only and makes no claim to represent an actual insurer's results.
