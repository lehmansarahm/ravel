--------------------------------------------------
-- Link updates
--------------------------------------------------

CREATE OR REPLACE FUNCTION add_link_fun ()
RETURNS TRIGGER
AS $$
import os
import sys

if 'PYTHONPATH' in os.environ:
    sys.path = os.environ['PYTHONPATH'].split(':') + sys.path
sys.path.append('/home/croftj/src/cli-ravel')
import ravel.net

sid = TD["new"]["sid"]
nid = TD["new"]["nid"]
isHost = TD["new"]["ishost"]
isActive = TD["new"]["ishost"]

ravel.net.addLink(sid, nid, isHost, isActive)

return None;
$$ LANGUAGE 'plpythonu' VOLATILE SECURITY DEFINER;

CREATE TRIGGER add_link_trigger
     AFTER INSERT ON tp
     FOR EACH ROW
   EXECUTE PROCEDURE add_link_fun();

CREATE OR REPLACE FUNCTION del_link_fun ()
RETURNS TRIGGER
AS $$
import os
import sys

if 'PYTHONPATH' in os.environ:
    sys.path = os.environ['PYTHONPATH'].split(':') + sys.path
sys.path.append('/home/croftj/src/cli-ravel')
import ravel.net

sid = TD["old"]["sid"]
nid = TD["old"]["nid"]

ravel.net.removeLink(sid, nid)

return None;
$$ LANGUAGE 'plpythonu' VOLATILE SECURITY DEFINER;

CREATE TRIGGER del_link_trigger
     AFTER DELETE ON tp
     FOR EACH ROW
   EXECUTE PROCEDURE del_link_fun();


--------------------------------------------------
-- Switch updates
--------------------------------------------------

CREATE OR REPLACE FUNCTION add_switch_fun ()
RETURNS TRIGGER
AS $$
import os
import sys

if 'PYTHONPATH' in os.environ:
    sys.path = os.environ['PYTHONPATH'].split(':') + sys.path
sys.path.append('/home/croftj/src/cli-ravel')
import ravel.net

sid = TD["new"]["sid"]
name = TD["new"]["name"]
dpid = TD["new"]["dpid"]
ip = TD["new"]["ip"]
mac = TD["new"]["mac"]

ravel.net.addSwitch(sid, name, dpid, ip, mac)

return None;
$$ LANGUAGE 'plpythonu' VOLATILE SECURITY DEFINER;

CREATE TRIGGER add_switch_trigger
     AFTER INSERT ON switches
     FOR EACH ROW
   EXECUTE PROCEDURE add_switch_fun();

CREATE OR REPLACE FUNCTION del_switch_fun ()
RETURNS TRIGGER
AS $$
import os
import sys

if 'PYTHONPATH' in os.environ:
    sys.path = os.environ['PYTHONPATH'].split(':') + sys.path
sys.path.append('/home/croftj/src/cli-ravel')
import ravel.net

sid = TD["old"]["sid"]
name = TD["old"]["name"]

ravel.net.removeSwitch(sid, name)

return None;
$$ LANGUAGE 'plpythonu' VOLATILE SECURITY DEFINER;

CREATE TRIGGER del_switch_trigger
     AFTER DELETE ON switches
     FOR EACH ROW
   EXECUTE PROCEDURE del_switch_fun();


--------------------------------------------------
-- Host updates
--------------------------------------------------

CREATE OR REPLACE FUNCTION add_host_fun ()
RETURNS TRIGGER
AS $$
import os
import sys

if 'PYTHONPATH' in os.environ:
    sys.path = os.environ['PYTHONPATH'].split(':') + sys.path
sys.path.append('/home/croftj/src/cli-ravel')
import ravel.net

hid = TD["new"]["hid"]
name = TD["new"]["name"]
ip = TD["new"]["ip"]
mac = TD["new"]["mac"]

ravel.net.addHost(hid, name, ip, mac)

return None;
$$ LANGUAGE 'plpythonu' VOLATILE SECURITY DEFINER;

CREATE TRIGGER add_host_trigger
     AFTER INSERT ON hosts
     FOR EACH ROW
   EXECUTE PROCEDURE add_host_fun();

CREATE OR REPLACE FUNCTION del_host_fun ()
RETURNS TRIGGER
AS $$
import os
import sys

if 'PYTHONPATH' in os.environ:
    sys.path = os.environ['PYTHONPATH'].split(':') + sys.path
sys.path.append('/home/croftj/src/cli-ravel')
import ravel.net

hid = TD["old"]["hid"]
name = TD["old"]["name"]

ravel.net.removeHost(hid, name)

return None;
$$ LANGUAGE 'plpythonu' VOLATILE SECURITY DEFINER;

CREATE TRIGGER del_host_trigger
     AFTER DELETE ON hosts
     FOR EACH ROW
   EXECUTE PROCEDURE del_host_fun();
