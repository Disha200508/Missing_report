import { useState } from "react";

export default function PhotoField() {
  const [preview, setPreview] = useState(null);
  return (
    <label>
      Photo *<small>Clear, front-facing, good light. JPG / PNG, max 10 MB.</small>
      <div className="drop">
        <input type="file" name="photo" accept="image/*" required
          onChange={(e) => { const f = e.target.files[0]; setPreview(f ? URL.createObjectURL(f) : null); }} />
        {preview && <img src={preview} alt="Preview" />}
      </div>
    </label>
  );
}
