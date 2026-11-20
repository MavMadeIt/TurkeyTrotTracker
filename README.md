# TurkeyTrotTracker

A consent-based live GPS tracker for four Turkey Trot runners: Gabby, Maverick, Vincent, and Jackson.

## Privacy and behavior
- Runners must choose their name, enter the private event code, and tap **Start sharing**.
- A runner can tap **Stop sharing** at any time.
- The organizer map requires a separate organizer code.
- Latest locations are held in server memory only; they are not saved to a database and clear when the service restarts.
- Keep both codes private. Do not post them in this public repository.
- Use this only with the runners' knowledge and permission.

## Deploy to Render
1. Create a Render account and choose **New > Blueprint**.
2. Connect this GitHub repository and deploy the `render.yaml` blueprint.
3. In the Render service's Environment settings, set:
   - `EVENT_CODE`: a private code shared only with participating runners.
   - `ORGANIZER_CODE`: a different private code shared only with authorized organizers.
4. Redeploy after setting the environment variables.
5. The runner page is the service URL. The organizer map is at `/organizer`.

The phone page requires HTTPS and location permission. Keep the organizer URL and organizer code private.

## Local development
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
set EVENT_CODE=your-private-event-code
set ORGANIZER_CODE=your-private-organizer-code
python app.py
```
