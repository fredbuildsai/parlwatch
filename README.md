# parlwatch

What do national parliaments really say about AI, and how is it changing over time? ParlWatch finds parliament
meetings on a topic, reuses existing transcripts when they exist (otherwise transcribes locally with quantized
models), attributes speakers, and extracts Q&A, positions and summaries into a database.

France (Assemblée nationale) first; Bundestag, Tweede Kamer and Congreso later via `CountryAdapter`.
See `configs/` for topics and per-country settings. Local models are always quantized (`quant: q4|q8`).
