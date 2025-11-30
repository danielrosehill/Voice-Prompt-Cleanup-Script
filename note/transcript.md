# Script for Speech-to-Text Audio Processing

**Description:** Creating a reusable open-source script to facilitate processing audio files for speech-to-text workflows.

**Transcribed:** 30 Nov 2025

---

## Transcript

Okay, so the purpose of this repository is going to be to create a reusable script for my own purposes and it'll be open source for anyone else who wishes to use it.

It's intended to facilitate the processing of audio files for use in speech-to-text workflows. So,

I'm just looking at the Gemini docs here for audio understanding, and it mentions downsampling. Yeah, 16 kilobits per second. Okay, so here is the idea with this repository and script. And I'm using an audio file deliberately in its kind of raw, rough-and-ready format in order to validate that the script works. So this will be called raw.mp3 or maybe raw.wav so we can include the conversion from whatever you start with, which in, you know, sort of more professional workflows, it might well be a wav, to what you want to send it up to the API in, which is almost certainly not going to be a wav.

So, when you're working with speech-to-text models, they are really tremendously powerful, and I have been using and developing, and I'm working on a number of voice workflows over the past year, let's say.

And what I've seen from experience is that the best way—the most successful way, I think, to approach generative AI and multimodal AI—is to not take the view: these things are so powerful, I can just send them anything and they'll do anything.

You have to do a lot of the legwork yourself, and when we're talking about audio, the same thing. So if you're using a multimodal API like Gemini,

rather than send a really scrappy audio file at the model that's in maybe the wrong bit rate and it's got a bunch of, you know, silences, and it's got pauses, and ums, and—I'm just doing this deliberately—stretches where—oh, let me just let—hold on, let me just finish this off. I'm gonna let John in the door. I said that deliberately. There's no John at my door, I hope.

But you might record it like this and you're like, well, it'll figure out that that interjection was not part of the prompt.

So there's two levels really to what I'm looking to do in this script and I'll use this repository to model out a couple of them, with the caveat in both cases that this is not—this script and this repository is intended just as a pipeline component. It's really on its own just for that purpose.

So the first and more—and more simplistic—and really the more pragmatic level that I do use at the moment all the time is when I'm recording this into Audacity, there's a few things that I will do almost automatically. One, I'll convert this to mono. Recording in stereo, I'll record this to mono. Secondly, I'll do that downsampling to 16 kilobits per second.

So when you have an API that you're targeting, which is going to downsample anything above that rate, there is zero point in going above it. And that 20 megabyte limit might seem very restrictive, but once you get clever with wrappers and sampling rates and the rest of it, you can actually stuff a lot of audio into that into that window. So that's number one. I would do that.

In Audacity we have a useful effect called silence truncation. And this is kind of my go-to for finding long pauses in the audio and doing that. Now this audio, as I'm looking at on the screen, the EQ seems to be reasonably okay to me, in the sense the levels I see are fairly good. But frequently, I'm recording these on my laptop or my phone or I'm not recording them on a proper mic like I am now.

And I think from the process from the perspective of STT processing, EQ, I don't think and DSing. There's different effects you might use for human listening that I don't think—I haven't seen anything to indicate that these actually really make a significant difference for ASR accuracy. But amplification seems to me like one that would make sense that you want to, if the whole operation of the model is in converting sound into text, you, you wanna make that sound audible without clipping it of course, which is going to lead to distortion. So I'll do amplification, I'll do silence truncation, and rendering out to mono and then I'll save it typically as mp3. Sometimes if it's a different speech-to-text model, I might do a different one. Those are—that's what I would consider the basic processing chain when we're—we're not talking AI yet. This is all just at the level of Audacity edits that I suspect can be scripted, which is why I've created this repository because even in the context of MCP tooling, it would make a lot more sense and speed up the workflow if there was just a quick automatic FFMPEG script I could run over the audio file, apply the batch of edits, and I don't need to manually open up the editor every time and make those same few changes.

The second more sophisticated level I don't think that is something I really feel needs to be there at the moment, but that would be really understanding the audio—and this would be AI—like saying, when Daniel said "John's at the door," that wasn't part of the transcription. Let's find that timestamp and let's cut it out. That would involve from what I understand at the moment actually doing speech-to-text before doing speech-to-text. You'd need whisper x for diarization. It would be a lot of work and I'm not sure there'd be a huge amount to gain. So I at the moment what I'm looking for in scope is just those first-level changes. But I'm just noting those for kind of a down-the-road improvement that could be made on this.
