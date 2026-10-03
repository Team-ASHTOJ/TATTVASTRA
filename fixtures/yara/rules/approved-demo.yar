rule approved_demo_marker
{
    meta:
        description = "Benign Tattvastra integration marker"
    strings:
        $marker = "TATTVASTRA_YARA_DEMO_MARKER"
    condition:
        $marker
}
