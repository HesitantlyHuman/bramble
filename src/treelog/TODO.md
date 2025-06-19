We want to set it up so that using standard python logging will still log in the tree logger, but also not prevent any other logging wrapper that people have made.

We want to set it up so that if a function is decorated, we will automatically fork for it (Why didn't we do this in the past, was there a good reason for it?)

We want to set it up so that we automatically capture std.out (but don't prevent it from normally printing, except maybe provide an option for that), and that it will route to the proper logger.
(How do we handle things like tqdm, where it is overwriting the output?)