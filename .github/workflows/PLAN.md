

The trigger will be on push and pull request  to master,i should never use pull_request_target because it fetche smy repo secret on runtime.

permission will be set to read contents: read, since we are not writing anything back to github in this workflow

Checkout, 
set up python 3.11
install,
test, 
Build image

These are the steps

I will find the repos for actions i want to use, find their release tags, and from there locate the commit and add the version comment next to sha # v4.2.2




I will keep them, however i will pin the actions to a SHA and remove the container text lint scan and point it at the Dockerfile that's currently unscanned

Use python3.11 to run flake 8