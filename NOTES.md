## TODO:
- Test compression ratios with different settings
- Create a new reading wrapper which uses the decompression
- Setup bramble to calculate and save metadata that we want in the UI while writing the logs. (start time, stop time, num entries, etc)
- Change the UI to use the new reading wrapper, and only load the metadata when creating the filtering screen

## Additional:
- Can we dynamically add the line of code? So that where the logging message came from can be audited?
- Only show some N previous logs by default in the streamlit view. Only show top level logs? (i.e. have no parent)
- Support displaying images and logging images

## Naming
branch_info -> parent, children, tags, metadata
metadata -> user added metadata (either for branch or log entry)
log_entry -> a particular entry in the logs; message, timestamp, message_type, metadata
why is the context version called `fork`, while doing the same action for a branch is called branch?