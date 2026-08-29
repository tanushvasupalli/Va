import asyncio
import edge_tts

async def main():
    voices = await edge_tts.list_voices()
    target = [v for v in voices if any(k in v['ShortName'] for k in ['hi-IN', 'te-IN', 'en-GB', 'en-IN'])]
    for v in target:
        print(f"[{v['Locale']}] {v['ShortName']} - Gender: {v['Gender']}")

if __name__ == "__main__":
    asyncio.run(main())
