# Deploying on Vercel

This Flask app can be deployed as a Vercel Python function. It requires a
separately hosted MySQL database; the app's data cannot be stored on Vercel's
temporary filesystem.

## Steps

1. Push this repository to GitHub. Keep `.env` out of Git.
2. Create a MySQL database with a provider that permits connections from
   Vercel. Create the database itself; on first app startup, SQLAlchemy creates
   the tables.
3. Import the GitHub repository in Vercel as a project. The root-level
   `vercel.json` routes requests to the Flask app in `app.py`.
4. Add these environment variables in the Vercel project settings:
   - `SECRET_KEY`: a unique, private random value
   - `DB_HOST`: MySQL hostname (include a port if required by your provider)
   - `DB_USER`
   - `DB_PASSWORD`
   - `DB_NAME`
   - `ADMIN_EMAIL` and `ADMIN_PASSWORD`: together, to create the initial
     administrator if that email does not already exist
   - `ADMIN_NAME`: optional; defaults to `System Admin`
5. Redeploy after setting the variables. Test registration/login, a screening,
   and PDF export using test data.

The app no longer creates an administrator with a public, hardcoded password.
Set both admin variables before the first deployment if you need an admin
account. The password is hashed before it is stored.

Do not use this demo deployment for real patient data unless the hosting,
database, privacy, security, and legal requirements for that data have been
reviewed.
