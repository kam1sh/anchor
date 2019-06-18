Common packaging information
============================

There is a few basic Anchor concepts common for all package implementation.


Packages
--------

Package
^^^^^^^

Package is a set of files that represents
different versions/formats of one project.
Package has next attributes:

- Retention policy with rules
  when a file could be removed or should be kept.
- Set of roles that references to a user or a group.

Package could be created manually from the UI or automatically,
when the new file could not be assigned to any existing package.
Administrator can change that behaviour
or bind new packages to default policy.


Package file
^^^^^^^^^^^^

Retention policy
^^^^^^^^^^^^^^^^

As said before, retention policy is a set of rules that defines
various conditions when a file may be removed or kept.
For example, if you run some policy, the next things will happen:

1. Policy finds all package files that meets any of the **drop** rules.
   Each rule consists of a multiple conditions, and all them
   should be satisfied to drop rules.
   In other words, logic of the abstract ``drop(a=1, b=2); drop(c=3, d=4)``
   policy could be represented as ``(a=1 AND b=2) OR (c=3 AND d=4)``.
2. Package files that meets any of the **keep** rules are excluded.
   Logic of the keep policy is the same as drop.
3. If there is a file that doesn't meet any of the criteria, it will be kept
   until the whole package quota will be exceeded. When this happens,
   Anchor will remove those files one by one, until there will be
   enough space to store the new file.

If user try to upload huge file and there is no available space
even after retention, he will get HTTP 413 (payload too large).

Roles
^^^^^

Like any other system, Anchor has access control features.
Model is similar to `GitLab`_:

- Package owner or administrator can do everything
  with the package, its files and other user permissions.
- Maintainer can do everything with files, edit some package settings
  (i.e. retention policy) and user permissions.
- Developer can upload new files and remove ones that belongs to him.
- Everyone else has access to read package info and download files.

.. _`GitLab`: https://docs.gitlab.com/ce/user/permissions.html

