import filecmp
import os
import shutil


def rsync_style_sync(src, dst):
    if os.path.isfile(src):
        shutil.copy2(src, dst)
        return

    if not os.path.exists(dst):
        os.makedirs(dst)

    comparison = filecmp.dircmp(src, dst)

    for file in comparison.left_only + comparison.diff_files:
        src_file = os.path.join(src, file)
        dst_file = os.path.join(dst, file)

        if os.path.isdir(src_file):
            shutil.copytree(src_file, dst_file)
        else:
            shutil.copy2(src_file, dst_file)  # copy2 preserves metadata (modification time)

    for file in comparison.right_only:
        dst_file = os.path.join(dst, file)
        if os.path.isdir(dst_file):
            shutil.rmtree(dst_file)
        else:
            os.remove(dst_file)

    for common_dir in comparison.common_dirs:
        rsync_style_sync(os.path.join(src, common_dir), os.path.join(dst, common_dir))
