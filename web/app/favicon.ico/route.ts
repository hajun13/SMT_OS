const ICON_BASE64 =
  "AAABAAEAEBAAAAAAIABoBAAAFgAAACgAAAAQAAAAIAAAAAEAGAAAAAAAAAMAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEBAQACAgIAAwMDAAQEBAAICAgABQUFAAYGBgAHBwcACQkJAAoKCgAMDAwADQ0NAA4ODgAPDw8AERERABISEgAUFBQAFRUVABYWFgAXFxcAGhoaABwcHAAdHR0AHh4eACAgIAAhISEAIiIiACQkJAA==";

export async function GET() {
  const buffer = Buffer.from(ICON_BASE64, "base64");
  return new Response(buffer, {
    headers: {
      "content-type": "image/x-icon",
      "cache-control": "public, max-age=31536000, immutable",
    },
  });
}
