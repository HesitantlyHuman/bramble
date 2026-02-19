## Compression approach:

Put the logs into chunks. Have the "compression" layer of the bramble chain hold some number of brotli compressors at once. Each compressor will be kept going until the its output reaches a set chunk size. When we receive messages, we will direct them to the assigned compressor for that particular branch. We will attempt to assign branches to chunks which already have a branch of that function.

Once a compressor's output has reached a set threshold, then we will finish the compression, and output a data chunk to the backend writer. Independently of chunk writing, we will be updating branch metadata as we go, including chunk IDs, so that we can locate any branch in just n+1 steps, where n is the number of chunks that branch has been written to (depends on the chunk size).

When a chunk finishes, we will create a new compressor and chunk to take its place. Each chunk will have a uuid so that we avoid collisions in the database.

When we are adding info the the chunk, we will be splitting that info so that we can identify the log message, vs the log metadata. Therefore, before every piece of compressed data, we will place a number for how long the next piece of data is. That way we can split them out, and then determine which is what by the order.

Each chunk will consist of multiple branches, so we will need to indicate, somehow, to which branch each log message belongs. There are two potential solutions to this:
- (1) Simply put the branch id each time we append a log entry. This is simple, and allows us to just keep compressing as we go, without holding on to anything.
- (2) Hold onto the messages in each branch of the compression chunk, until we have enough, and then do them in branch order. This way, we only need to say the id once each time. The compression would be better, but we would use more memory.

What if we only put the branch id if it has changed? And since we are routing to multiple compressors anyways, it may not change that often? Best of both worlds?

## TODO:
- Test the decompression for brotli, to determine how it works
- Build a simple compression and decompression setup for bramble types, and test. See what our ratios are like, work out kinks
- Create a new backend wrapper that does the compression, and then calls a database specific adapter when necessary
- Swap the old backend for the new compressing backend
- Create a new reading wrapper which uses the decompression
- Setup bramble to calculate and save metadata that we want in the UI while writing the logs.
- Change the UI to use the new reading wrapper, and only load the metadata when creating the filtering screen

## Additional:
- Can we dynamically add the line of code? So that where the logging message came from can be audited?
- Only show some N previous logs by default in the streamlit view. Only show top level logs (i.e. have no parent)