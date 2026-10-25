"""Local operator command: promote an existing registered user, never set a password."""
import argparse
from sqlalchemy import select
from sqlalchemy.orm import Session
from main import User, app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('email', help='Email of an existing registered account')
    args = parser.parse_args()
    with Session(app.state.engine) as db:
        user = db.scalar(select(User).where(User.email == args.email.strip().lower()))
        if user is None:
            parser.exit(1, 'Account not found. Start the API and register the account first.\n')
        user.role = 'admin'
        db.commit()
    print('Existing account promoted to admin.')

if __name__ == '__main__':
    main()
