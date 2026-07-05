import os
import subprocess
import tkinter
from pathlib import Path

# os.environ["MAGICK_HOME "] = os.getcwd() + R"\imageMagick"


def compress_dir_jpg(
    source_dir: str,
    output_dir: str,
    quality: int,
    label_var: tkinter.StringVar,
    label_current_no: tkinter.StringVar,
    progress_bar_fn,
    compress_btn_handle: tkinter.Button,
    stop_btn_handle: tkinter.Button,
    error_var: tkinter.StringVar,
    extension: str = ".jpg",
):
    try:
        source_dir = source_dir.rstrip("\\")
        output_dir = output_dir.rstrip("\\")
        total_count = recr_struct_count_im(source_dir, output_dir, extension)
        
        if label_var is not None:
            label_var.set("ROZPOCZĘTO")
        if label_current_no is not None:
            label_current_no.set("0/" + str(total_count))
        image_counter = 0
        return_code = 0
        if isinstance(extension, str):
            extension = [extension]
        for dirpath, dirnames, filenames in os.walk(source_dir):
            if len(filenames):
                deep_output = output_dir + dirpath[len(source_dir) :]
                for ext in extension:
                    if sum([ext in f for f in filenames]):
                        image_counter, return_code = compress_dir_proc(
                            source_dir=dirpath,
                            output_dir=deep_output,
                            quality=quality,
                            image_counter=image_counter,
                            total_count=total_count,
                            label_var=label_var,
                            label_current_no=label_current_no,
                            progress_bar_fn=progress_bar_fn,
                            stop_btn_handle=stop_btn_handle,
                            error_var=error_var,
                            extension=ext,
                        )
                        if return_code:
                            raise ChildProcessError("Anulowano!")

    except Exception as e:
        print("Error: ", e)
        # if e is ChildProcessError:
        if error_var is not None:
            error_var.set(e)
        # else:
        #     error_var.set("Coś poszło nie tak")

    if stop_btn_handle is not None:
        stop_btn_handle.configure(command=None)
        stop_btn_handle.grid_forget()
        
    if label_var is not None:
        label_var.set("ZAKOŃCZONO")
    if label_current_no is not None:
        label_current_no.set("")
    if compress_btn_handle is not None:
        compress_btn_handle.configure(state=tkinter.NORMAL)


def compress_dir_proc(
    source_dir: str,
    output_dir: str,
    quality: int,
    image_counter: int,
    total_count: int,
    label_var: tkinter.StringVar,
    label_current_no: tkinter.StringVar,
    progress_bar_fn,
    stop_btn_handle: tkinter.Button,
    error_var: tkinter.StringVar,
    extension: str = ".jpg",
):
    magick_path = Path(os.getcwd()) / "imageMagick" / "magick.exe"
    cmd = [
        str(magick_path), "mogrify",
        "-path", str(output_dir),
        # resize to 4K (3840x2160) if larger, preserving aspect ratio
        "-resize", "3840x2160^>",
        "-filter", "Triangle",
        "-define", "filter:support=2",
        "-unsharp", "0.25x0.08+8.3+0.045",
        "-dither", "None",
        # Optimize JPEG and PNG compression settings
        "-quality", str(quality),
        "-define", "jpeg:fancy-upsampling=off",
        "-define", "png:compression-filter=5",
        "-define", "png:compression-level=9",
        "-define", "png:compression-strategy=1",
        "-interlace", "none",
        "-colorspace", "sRGB",
        "-clamp",
        "-verbose",
        str(Path(source_dir) / f"*{extension}")
    ]
    print(cmd)
    prev_filename = ""
    proc_im = execute(cmd)
    if stop_btn_handle is not None:
        stop_btn_handle.configure(command=lambda: proc_im.terminate())
    return_code = 0

    for line in read_process_output(proc_im, cmd):
        if line == 1:
            error_var.set("Anulowano!")
            return_code = 1
            break
        filename = extract_filename(line, extension)
        if filename != extension:
            if label_var is not None:
                label_var.set(filename + extension)
            if filename != prev_filename:
                prev_filename = filename
                image_counter += 1
                if label_current_no is not None:
                    label_current_no.set(
                    str(image_counter) + "/" + str(total_count)
                )
                if progress_bar_fn is not None:
                    progress_bar_fn(float(image_counter / total_count))

    return image_counter, return_code


def recr_struct_count_im(source_dir, output_dir, extension):
    no_im = 0
    for dirpath, dirnames, filenames in os.walk(source_dir):
        structure = output_dir + dirpath[len(source_dir) :]
        if not os.path.isdir(structure):
            os.mkdir(structure)
        else:
            print("Folder does already exits! " + structure)
        if isinstance(extension, str):
            extension = [extension]

        for ext in extension:
            no_im += len(
                [
                    f
                    for f in filenames
                    if os.path.isfile(os.path.join(source_dir, f))
                    and ext in f.lower()
                ]
            )
    return no_im


def calculate_images(source_dir, extension):
    # and recreate structure
    extension = extension.lower()

    onlyfiles_with_ext = [
        f
        for f in os.listdir(source_dir)
        if os.path.isfile(os.path.join(source_dir, f))
        and extension in f.lower()
    ]

    return len(onlyfiles_with_ext)


def extract_filename(line, extension):
    line_lower = line.lower()
    filename = line[line_lower.rindex("\\") + 1 : line_lower.rindex(extension)]
    return filename


def execute(cmd):
    popen = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, universal_newlines=True
    )
    return popen


def read_process_output(popen, cmd):
    for stdout_line in iter(popen.stdout.readline, ""):
        yield stdout_line
    popen.stdout.close()
    return_code = popen.wait()
    if return_code:
        yield return_code
        raise subprocess.CalledProcessError(return_code, cmd)


if __name__ == "__main__":
    # source_dir = (
    #     "D:\OneDrive - Politechnika Wroclawska\projectsPython\imageCompressor\images_in"
    # )
    # output_dir = "D:\OneDrive - Politechnika Wroclawska\projectsPython\imageCompressor\images_out"
    # extract_filename(
    #     R"D:\OneDrive - Politechnika Wroclawska\projectsPython\imageCompressor\images_in\P5130202.JPG JPEG 4608x3456 4608x3456+0+0 8-bit sRGB 6.83107MiB 0.172u 0:00.170>3840x2880 3840x2880+0+0 8-bit sRGB 860718B 1.313u 0:01.319",
    #     ".jpg",
    # )
    source_dir = R"C:\Users\lapci\Pictures\magick_tests\test"
    output_dir = R"C:\Users\lapci\Pictures\magick_tests\test_comp"
    # print(recr_struct_count_im(source_dir, output_dir, ".jpg"))
    # print(calculate_images(source_dir, ".jpg"))
    compress_dir_jpg(
        source_dir=source_dir,
        output_dir=output_dir,
        progress_bar_fn=None,
        compress_btn_handle=None,
        label_var=None,
        label_current_no=None,
        stop_btn_handle=None,
        error_var=None,
        quality=80,
    )
