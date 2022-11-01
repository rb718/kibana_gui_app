
from .main import scrape
from optparse import OptionParser

parser = OptionParser()
parser.add_option("-u", "--username", dest="username", default=None,
                  help="Username to be used if login is required")
parser.add_option("-p", "--password",dest="password", default=None,
                  help="Password to be used if login is required")

(options, args) = parser.parse_args()

if __name__=="__main__":
    scrape(options.username, options.password)
