# Final submission checklist

The implementation files are prepared. Publishing, recording and the final portal submission still require your own account actions. No public repository, hosted application, video or final submission has been created by this package.

## Check the original organizer document

- Open the linked full submission guidelines. Verify the mandatory README headings, permitted AI assistance, team rules, required video length and file/link format.
- The pasted case study limits the live demonstration to five minutes and the deck to seven slides. The supplied screenshots described a separate ten-minute video walkthrough. Follow the latest official instruction if these differ.
- Check the deadline in the actual invitation/portal and its timezone. Earlier pasted material indicated 11 October 2026. Do not rely on that date without checking the portal now.

## Review and run

- Extract the project fully and run `start.bat` / `bash start.sh`.
- Install/cache FinBERT and confirm the active backend before recording.
- Inspect every dashboard page on your laptop. Browser visual QA could not run in the build environment.
- Run the tests and rehearse the five-minute demo. Read the source explanation and AI disclosure.
- Confirm official name/team/institution attribution in the README and slides. Add any required team members.

## Publish the source

- Create a **public** GitHub repository in your own account.
- Upload the project contents including `src`, `frontend/src`, `frontend/dist`, `data`, `tests`, `docs`, dependency files, README and LICENSE.
- Exclude `.venv`, `node_modules`, `runtime`, `.env`, database files, downloaded model weights and personal tokens.
- Replace `YOUR_USERNAME` in the README clone command with your repository owner.
- Confirm `docs/presentation.pdf` is present and accessible. Keep the original seven-slide deck editable as `docs/presentation.pptx`.
- Open the repo and files signed out to verify accessibility.

For Git CLI users, from the `riskpulse` folder:

```bash
git init
git add .
git commit -m "Implement RiskPulse risk engine and index rebalancer"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/riskpulse.git
git push -u origin main
```

Create the empty public repository first and replace the URL. Authenticate using your own GitHub tooling. Never paste a personal token into the source or README.

## Record and submit

- Record the working app with your narration using the provided walkthrough script.
- Upload the video in the organizer's required format/access mode and test it signed out.
- Replace every link placeholder in `SUBMISSION_TEMPLATE.txt` and add the final video/repository links to README.
- Paste the completed summary and real URLs into the DoSelect answer box.
- If the portal requires a file, attach the presentation PDF or the exact file/package the current guidelines request. The Choose File control accepts an attachment; it does not replace the required source/video links unless the guidelines say so.
- Click Save, then follow Continue to Submission Page and complete the final submission. Confirm the portal shows submission success, not merely a saved draft.
